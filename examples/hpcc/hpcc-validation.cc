/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * HPCC Validation — refactored simulation using HpccConfig (YAML-based).
 * Step 2: Config loading + ns3 defaults + IntHeader/Pint + topology/node setup.
 */

#include <iostream>
#include <fstream>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <string>
#include <sstream>
#include <time.h>
#include <fmt/format.h>
#include "ns3/core-module.h"
#include "ns3/qbb-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/global-route-manager.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/packet.h"
#include "ns3/error-model.h"
#include <ns3/rdma-client.h>
#include <ns3/rdma-client-helper.h>
#include <ns3/rdma-driver.h>
#include <ns3/switch-node.h>
#include <ns3/sim-setting.h>
#include "hpcc-config.h"

using namespace ns3;
using namespace std;

// Helper: strip \r from stream (handles CRLF files on Unix)
static void strip_cr(std::ifstream& f) {
	while (f.peek() == '\r') f.get();
}

static bool ValidateFlowFile(const std::string& path, uint32_t expectedFlows, uint32_t nodeNum) {
	std::ifstream input(path.c_str());
	if (!input.is_open()) {
		fmt::print(stderr, "ERROR: Cannot reopen flow file for validation: {}\n", path);
		return false;
	}

	std::string line;
	uint64_t headerCount = 0;
	if (!std::getline(input, line)) {
		fmt::print(stderr, "ERROR: Flow file is empty: {}\n", path);
		return false;
	}
	std::istringstream header(line);
	if (!(header >> headerCount)) {
		fmt::print(stderr, "ERROR: Flow file header is not an integer in {}\n", path);
		return false;
	}
	if (headerCount != expectedFlows) {
		fmt::print(stderr,
		           "ERROR: Flow file header changed while reading {}: first read {} but validation read {}\n",
		           path, expectedFlows, headerCount);
		return false;
	}

	uint64_t parsedRows = 0;
	uint64_t lineNo = 1;
	double previousStart = -1.0;
	while (std::getline(input, line)) {
		lineNo++;
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (line.find_first_not_of(" \t") == std::string::npos) continue;
		if (line.find_first_not_of(" \t") == line.find('#')) continue;

		std::istringstream row(line);
		uint32_t src = 0, dst = 0, pg = 0, dport = 0, size = 0;
		double start = 0.0;
		std::string extra;
		if (!(row >> src >> dst >> pg >> dport >> size >> start) || (row >> extra)) {
			fmt::print(stderr,
			           "ERROR: Flow file {} line {} must have exactly 6 columns: src dst pg dport size start_time\n",
			           path, lineNo);
			return false;
		}
		if (src >= nodeNum || dst >= nodeNum) {
			fmt::print(stderr,
			           "ERROR: Flow file {} line {} has src={} dst={} outside node count {}\n",
			           path, lineNo, src, dst, nodeNum);
			return false;
		}
		if (src == dst) {
			fmt::print(stderr, "ERROR: Flow file {} line {} has src == dst ({})\n", path, lineNo, src);
			return false;
		}
		if (pg >= SwitchMmu::qCnt) {
			fmt::print(stderr, "ERROR: Flow file {} line {} has invalid priority group {}\n", path, lineNo, pg);
			return false;
		}
		if (size == 0) {
			fmt::print(stderr, "ERROR: Flow file {} line {} has zero-byte flow\n", path, lineNo);
			return false;
		}
		if (start < 0.0) {
			fmt::print(stderr, "ERROR: Flow file {} line {} has negative start time {}\n", path, lineNo, start);
			return false;
		}
		if (previousStart >= 0.0 && start + 1e-12 < previousStart) {
			fmt::print(stderr,
			           "ERROR: Flow file {} line {} is not sorted by start time: {} after {}\n",
			           path, lineNo, start, previousStart);
			return false;
		}
		previousStart = start;
		parsedRows++;
	}

	if (parsedRows != expectedFlows) {
		fmt::print(stderr,
		           "ERROR: Flow file {} header says {} flow(s), but parsed {} data row(s)\n",
		           path, expectedFlows, parsedRows);
		return false;
	}

	return true;
}

static void PrintProgressBar(Time stopTime, Time interval) {
	const double nowSeconds = Simulator::Now().GetSeconds();
	const double stopSeconds = stopTime.GetSeconds();
	const double fraction = stopSeconds > 0 ? std::min(1.0, nowSeconds / stopSeconds) : 1.0;
	constexpr uint32_t width = 40;
	const uint32_t filled = std::min(width, static_cast<uint32_t>(fraction * width));
	std::string bar(width, ' ');

	for (uint32_t i = 0; i < filled; ++i) {
		bar[i] = '=';
	}
	if (filled < width) {
		bar[filled] = '>';
	}

	fmt::print(stderr,
	           "\rHPCC progress [{}] {:6.2f}% sim {:8.6f}/{:8.6f}s events {}",
	           bar, fraction * 100.0, nowSeconds, stopSeconds, Simulator::GetEventCount());
	std::fflush(stderr);

	if (Simulator::Now() + interval < stopTime) {
		Simulator::Schedule(interval, &PrintProgressBar, stopTime, interval);
	}
}

static std::string FormatWallDuration(uint64_t seconds) {
	const uint64_t days = seconds / 86400;
	seconds %= 86400;
	const uint64_t hours = seconds / 3600;
	seconds %= 3600;
	const uint64_t minutes = seconds / 60;
	seconds %= 60;
	return fmt::format("{}d:{:02}h:{:02}m:{:02}s", days, hours, minutes, seconds);
}

static std::string FormatRemainingWallTime(double simNowSeconds,
                                           double simStopSeconds,
                                           uint64_t elapsedWallSeconds) {
	if (simStopSeconds <= 0.0 || simNowSeconds <= 0.0) {
		return "unknown";
	}
	if (simNowSeconds >= simStopSeconds) {
		return FormatWallDuration(0);
	}
	const double remainingWallSeconds =
	    (static_cast<double>(elapsedWallSeconds) / simNowSeconds) *
	    (simStopSeconds - simNowSeconds);
	return FormatWallDuration(static_cast<uint64_t>(remainingWallSeconds + 0.5));
}

NS_LOG_COMPONENT_DEFINE("HpccValidation");

/************************************************
 * Runtime variables (populated from cfg or during simulation)
 ***********************************************/
std::ifstream topof, flowf, tracef;
NodeContainer n;
uint64_t nic_rate;
uint64_t maxRtt, maxBdp;

// Populated from cfg in main(), used by helper functions
uint32_t packet_payload_size;
uint32_t has_win, global_t;
bool fs_disable_window = true;  // HPCC-FS rate-only (cc_mode 11); set from cfg in main()

struct Interface {
	uint32_t idx;
	bool up;
	uint64_t delay;
	uint64_t bw;
	Interface() : idx(0), up(false) {}
};
map<Ptr<Node>, map<Ptr<Node>, Interface> > nbr2if;
map<Ptr<Node>, map<Ptr<Node>, vector<Ptr<Node> > > > nextHop;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairDelay;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairTxDelay;
map<uint32_t, map<uint32_t, uint64_t> > pairBw;
map<Ptr<Node>, map<Ptr<Node>, uint64_t> > pairBdp;
map<uint32_t, map<uint32_t, uint64_t> > pairRtt;

std::vector<Ipv4Address> serverAddress;

// maintain port number for each host pair
std::unordered_map<uint32_t, unordered_map<uint32_t, uint16_t> > portNumder;

struct FlowInput {
	uint32_t src, dst, pg, maxPacketCount, port, dport;
	double start_time;
	uint32_t idx;
};
FlowInput flow_input = {0};
uint32_t flow_num;
uint32_t completed_flow_num = 0;

static std::chrono::steady_clock::time_point status_start_wall;
static std::chrono::steady_clock::time_point status_last_snapshot_wall;
static bool status_wall_clock_ready = false;
static std::mutex status_snapshot_mutex;
static std::string status_snapshot;
static std::atomic<bool> status_thread_running(false);
static std::mutex status_thread_mutex;
static std::condition_variable status_thread_cv;
static std::thread status_thread;
static Time status_stop_time;

void MaybeRefreshStatusSnapshot(NodeContainer* nodes, Time stopTime, bool force);
void PrintStatusSnapshot();

/************************************************
 * Helper functions
 ***********************************************/
void ReadFlowInput() {
	if (flow_input.idx < flow_num) {
		if (!(flowf >> flow_input.src >> flow_input.dst >> flow_input.pg
		      >> flow_input.dport >> flow_input.maxPacketCount >> flow_input.start_time)) {
			NS_FATAL_ERROR("Failed to parse flow row " << (flow_input.idx + 2)
			               << "; the header count is larger than the available valid rows");
		}
		if (flow_input.src >= n.GetN() || flow_input.dst >= n.GetN()) {
			NS_FATAL_ERROR("Flow row " << (flow_input.idx + 2)
			               << " references node outside topology: src=" << flow_input.src
			               << " dst=" << flow_input.dst << " nodes=" << n.GetN());
		}
		if (n.Get(flow_input.src)->GetNodeType() != 0 || n.Get(flow_input.dst)->GetNodeType() != 0) {
			NS_FATAL_ERROR("Flow row " << (flow_input.idx + 2)
			               << " must use server nodes: src=" << flow_input.src
			               << " dst=" << flow_input.dst);
		}
		// fmt::print("Read flow: src={} dst={} pg={} dport={} maxPkt={} start={}\n",
		           // flow_input.src, flow_input.dst, flow_input.pg,
		           // flow_input.dport, flow_input.maxPacketCount, flow_input.start_time);
	}
}

void ScheduleFlowInputs() {
	while (flow_input.idx < flow_num && Seconds(flow_input.start_time) == Simulator::Now()) {
		uint32_t port = portNumder[flow_input.src][flow_input.dst]++;
		RdmaClientHelper clientHelper(
			flow_input.pg,
			serverAddress[flow_input.src],
			serverAddress[flow_input.dst],
			port, flow_input.dport, flow_input.maxPacketCount,
			// HPCC-FS (cc_mode 11) defaults to rate-only: var_win's GetWin = m_win*rate/NIC_line is
			// sized for the NIC, not the (smaller, multi-hop) bottleneck path, which capped goodput
			// below the RCP fair rate. Switch RCP keeps queues bounded already, so window=0 (no cap)
			// lets the long flow take its fair share. The fs_disable_window knob (default true) turns
			// this off for the ablation. cc_mode 3 unchanged.
			(has_win && !(IntHeader::mode == IntHeader::FS && fs_disable_window)) ? (global_t == 1 ? maxBdp : pairBdp[n.Get(flow_input.src)][n.Get(flow_input.dst)]) : 0,
			global_t == 1 ? maxRtt : pairRtt[flow_input.src][flow_input.dst]);
		ApplicationContainer appCon = clientHelper.Install(n.Get(flow_input.src));
		appCon.Start(Time(0));
		flow_input.idx++;
		ReadFlowInput();
	}
	MaybeRefreshStatusSnapshot(&n, status_stop_time, false);
	if (flow_input.idx < flow_num) {
		Simulator::Schedule(Seconds(flow_input.start_time) - Simulator::Now(), ScheduleFlowInputs);
	} else {
		flowf.close();
	}
}

Ipv4Address node_id_to_ip(uint32_t id) {
	return Ipv4Address(0x0b000001 + ((id / 256) * 0x00010000) + ((id % 256) * 0x00000100));
}

uint32_t ip_to_node_id(Ipv4Address ip) {
	return (ip.Get() >> 8) & 0xffff;
}

void qp_finish(FILE* fout, Ptr<RdmaQueuePair> q) {
	completed_flow_num++;
	MaybeRefreshStatusSnapshot(&n, status_stop_time, false);
	uint32_t sid = ip_to_node_id(q->sip), did = ip_to_node_id(q->dip);
	uint64_t base_rtt = pairRtt[sid][did], b = pairBw[sid][did];
	uint32_t total_bytes = q->m_size + ((q->m_size - 1) / packet_payload_size + 1)
	    * (CustomHeader::GetStaticWholeHeaderSize() - IntHeader::GetStaticSize());
	uint64_t standalone_fct = base_rtt + total_bytes * 8000000000lu / b;
	fprintf(fout, "%08x %08x %u %u %lu %lu %lu %lu\n",
	        q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->m_size,
	        q->startTime.GetTimeStep(), (Simulator::Now() - q->startTime).GetTimeStep(),
	        standalone_fct);
	fflush(fout);
	Ptr<Node> dstNode = n.Get(did);
	Ptr<RdmaDriver> rdma = dstNode->GetObject<RdmaDriver>();
	rdma->m_rdma->DeleteRxQp(q->sip.Get(), q->m_pg, q->sport);
}

void get_pfc(FILE* fout, Ptr<QbbNetDevice> dev, uint32_t type, uint32_t qIndex) {
	fprintf(fout, "%lu %u %u %u %u %u\n", Simulator::Now().GetTimeStep(),
	        dev->GetNode()->GetId(), dev->GetNode()->GetNodeType(),
	        dev->GetIfIndex(), qIndex, type);
}

// Queue length monitoring variables
uint32_t qlen_dump_interval = 100000000;
uint32_t qlen_mon_interval = 100;
uint64_t qlen_mon_start_ns, qlen_mon_end_ns;

struct QlenDistribution {
	vector<uint32_t> cnt;
	void add(uint32_t qlen) {
		uint32_t kb = qlen / 1000;
		if (cnt.size() < kb + 1) cnt.resize(kb + 1);
		cnt[kb]++;
	}
};
map<uint32_t, map<uint32_t, QlenDistribution> > queue_result;

struct BottleneckSample {
	uint32_t maxEgressBytes = 0;
	uint32_t maxIngressSharedBytes = 0;
	uint32_t maxIngressBytes = 0;
	uint32_t maxHdrmBytes = 0;
	uint32_t minPfcThreshold = 0xffffffff;
	uint32_t kmin = 0;
	uint32_t kmax = 0;
	uint32_t samples = 0;
	bool ecnSeen = false;
	bool pauseSeen = false;
};
map<uint32_t, map<uint32_t, map<uint32_t, BottleneckSample> > > bottleneck_result;

void update_bottleneck_sample(Ptr<SwitchNode> sw, uint32_t switchId, uint32_t port, uint32_t pg) {
	BottleneckSample& sample = bottleneck_result[switchId][port][pg];
	const uint32_t egress = sw->m_mmu->egress_bytes[port][pg];
	const uint32_t ingress = sw->m_mmu->ingress_bytes[port][pg];
	const uint32_t hdrm = sw->m_mmu->hdrm_bytes[port][pg];
	const uint32_t shared = sw->m_mmu->GetSharedUsed(port, pg);
	const uint32_t pfcThreshold = sw->m_mmu->GetPfcThreshold(port);

	sample.maxEgressBytes = std::max(sample.maxEgressBytes, egress);
	sample.maxIngressSharedBytes = std::max(sample.maxIngressSharedBytes, shared);
	sample.maxIngressBytes = std::max(sample.maxIngressBytes, ingress);
	sample.maxHdrmBytes = std::max(sample.maxHdrmBytes, hdrm);
	sample.minPfcThreshold = std::min(sample.minPfcThreshold, pfcThreshold);
	sample.kmin = sw->m_mmu->kmin[port];
	sample.kmax = sw->m_mmu->kmax[port];
	sample.samples++;
	if (sample.kmin > 0 && egress >= sample.kmin) sample.ecnSeen = true;
	if (sw->m_mmu->paused[port][pg] || hdrm > 0 || shared >= pfcThreshold) sample.pauseSeen = true;
}

void monitor_buffer(FILE* qlen_output, NodeContainer* n) {
	for (uint32_t i = 0; i < n->GetN(); i++) {
		if (n->Get(i)->GetNodeType() == 1) {
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n->Get(i));
			if (queue_result.find(i) == queue_result.end()) queue_result[i];
			for (uint32_t j = 1; j < sw->GetNDevices(); j++) {
				uint32_t size = 0;
				for (uint32_t k = 0; k < SwitchMmu::qCnt; k++) {
					size += sw->m_mmu->egress_bytes[j][k];
					update_bottleneck_sample(sw, i, j, k);
				}
				queue_result[i][j].add(size);
			}
		}
	}
	if (Simulator::Now().GetTimeStep() % qlen_dump_interval == 0) {
		fprintf(qlen_output, "time: %lu\n", Simulator::Now().GetTimeStep());
		for (auto& it0 : queue_result)
			for (auto& it1 : it0.second) {
				fprintf(qlen_output, "%u %u", it0.first, it1.first);
				auto& dist = it1.second.cnt;
				for (uint32_t i = 0; i < dist.size(); i++)
					fprintf(qlen_output, " %u", dist[i]);
				fprintf(qlen_output, "\n");
			}
		fflush(qlen_output);
	}
	MaybeRefreshStatusSnapshot(n, status_stop_time, false);
	if (Simulator::Now().GetTimeStep() < qlen_mon_end_ns)
		Simulator::Schedule(NanoSeconds(qlen_mon_interval), &monitor_buffer, qlen_output, n);
}

void write_bottleneck_summary(FILE* output) {
	if (output == nullptr) return;

	fprintf(output,
	        "# sw port pg max_egress_bytes kmin kmax max_ratio "
	        "max_shared_bytes max_ingress_bytes max_hdrm_bytes min_pfc_threshold "
	        "ecn_seen pause_seen samples\n");

	bool found = false;
	uint32_t bestSw = 0, bestPort = 0, bestPg = 0;
	BottleneckSample best;
	double bestRatio = 0.0;

	for (const auto& swEntry : bottleneck_result) {
		for (const auto& portEntry : swEntry.second) {
			for (const auto& pgEntry : portEntry.second) {
				const uint32_t swId = swEntry.first;
				const uint32_t port = portEntry.first;
				const uint32_t pg = pgEntry.first;
				const BottleneckSample& sample = pgEntry.second;
				const double ratio = sample.kmax > 0
				                         ? static_cast<double>(sample.maxEgressBytes) / sample.kmax
				                         : static_cast<double>(sample.maxEgressBytes);
				const uint32_t minPfcThreshold =
				    sample.minPfcThreshold == 0xffffffff ? 0 : sample.minPfcThreshold;

				fprintf(output, "%u %u %u %u %u %u %.6f %u %u %u %u %u %u %u\n",
				        swId, port, pg, sample.maxEgressBytes, sample.kmin, sample.kmax,
				        ratio, sample.maxIngressSharedBytes, sample.maxIngressBytes,
				        sample.maxHdrmBytes, minPfcThreshold, sample.ecnSeen ? 1 : 0,
				        sample.pauseSeen ? 1 : 0, sample.samples);

				if (pg == 0) continue;
				if (!found || ratio > bestRatio ||
				    (ratio == bestRatio && sample.maxEgressBytes > best.maxEgressBytes)) {
					found = true;
					bestSw = swId;
					bestPort = port;
					bestPg = pg;
					best = sample;
					bestRatio = ratio;
				}
			}
		}
	}

	if (found) {
		const uint32_t minPfcThreshold =
		    best.minPfcThreshold == 0xffffffff ? 0 : best.minPfcThreshold;
		fprintf(output,
		        "max_overall %u %u %u %u %u %u %.6f %u %u %u %u %u %u %u\n",
		        bestSw, bestPort, bestPg, best.maxEgressBytes, best.kmin, best.kmax,
		        bestRatio, best.maxIngressSharedBytes, best.maxIngressBytes,
		        best.maxHdrmBytes, minPfcThreshold, best.ecnSeen ? 1 : 0,
		        best.pauseSeen ? 1 : 0, best.samples);
	}
	fflush(output);
}

struct FlowStatus {
	uint32_t started = 0;
	uint32_t completed = 0;
	uint32_t pending = 0;
	uint32_t active = 0;
	uint32_t activeQps = 0;
	uint64_t bytesLeft = 0;
	uint64_t bytesInFlight = 0;
};

struct BottleneckStatus {
	bool found = false;
	uint32_t switchId = 0;
	uint32_t port = 0;
	uint32_t pg = 0;
	uint32_t queueBytes = 0;
	uint32_t kmin = 0;
	uint32_t kmax = 0;
	uint32_t pfcThreshold = 0;
	uint32_t pausedQueues = 0;
	uint32_t ecnQueues = 0;
	uint32_t sharedBufferBytes = 0;
	uint32_t bufferBytes = 0;
	uint64_t totalEgressBytes = 0;
	double kmaxRatio = 0.0;
};

FlowStatus CollectFlowStatus(NodeContainer* nodes) {
	FlowStatus status;
	status.started = flow_input.idx;
	status.completed = completed_flow_num;
	status.pending = status.started <= flow_num ? flow_num - status.started : 0;
	status.active = status.started >= status.completed ? status.started - status.completed : 0;

	for (uint32_t i = 0; i < nodes->GetN(); i++) {
		Ptr<Node> node = nodes->Get(i);
		if (node->GetNodeType() != 0) continue;
		for (uint32_t j = 1; j < node->GetNDevices(); j++) {
			Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(node->GetDevice(j));
			if (dev == nullptr || dev->GetRdmaQueue() == nullptr) continue;
			Ptr<RdmaEgressQueue> rdmaQueue = dev->GetRdmaQueue();
			if (rdmaQueue->m_qpGrp == nullptr) continue;
			for (uint32_t k = 0; k < rdmaQueue->GetFlowCount(); k++) {
				Ptr<RdmaQueuePair> qp = rdmaQueue->GetQp(k);
				if (qp == nullptr || qp->IsFinished()) continue;
				status.activeQps++;
				status.bytesLeft += qp->GetBytesLeft();
				if (qp->snd_nxt >= qp->snd_una) {
					status.bytesInFlight += qp->snd_nxt - qp->snd_una;
				}
			}
		}
	}
	return status;
}

BottleneckStatus CollectBottleneckStatus(NodeContainer* nodes) {
	BottleneckStatus status;
	for (uint32_t i = 0; i < nodes->GetN(); i++) {
		if (nodes->Get(i)->GetNodeType() != 1) continue;
		Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(nodes->Get(i));
		if (sw == nullptr || sw->m_mmu == nullptr) continue;
		for (uint32_t port = 1; port < sw->GetNDevices() && port < SwitchMmu::pCnt; port++) {
			for (uint32_t pg = 1; pg < SwitchMmu::qCnt; pg++) {
				const uint32_t bytes = sw->m_mmu->egress_bytes[port][pg];
				const uint32_t kmax = sw->m_mmu->kmax[port];
				const uint32_t kmin = sw->m_mmu->kmin[port];
				const double ratio = kmax > 0 ? static_cast<double>(bytes) / kmax
				                              : static_cast<double>(bytes);
				status.totalEgressBytes += bytes;
				if (sw->m_mmu->paused[port][pg]) status.pausedQueues++;
				if (kmin > 0 && bytes >= kmin) status.ecnQueues++;
				if (!status.found || ratio > status.kmaxRatio ||
				    (ratio == status.kmaxRatio && bytes > status.queueBytes)) {
					status.found = true;
					status.switchId = sw->GetId();
					status.port = port;
					status.pg = pg;
					status.queueBytes = bytes;
					status.kmin = kmin;
					status.kmax = kmax;
					status.pfcThreshold = sw->m_mmu->GetPfcThreshold(port);
					status.sharedBufferBytes = sw->m_mmu->shared_used_bytes;
					status.bufferBytes = sw->m_mmu->buffer_size;
					status.kmaxRatio = ratio;
				}
			}
		}
	}
	return status;
}

const char* GetBottleneckState(const BottleneckStatus& status) {
	if (!status.found) return "none";
	if (status.kmax > 0 && status.queueBytes >= status.kmax) return "above-kmax";
	if (status.kmin > 0 && status.queueBytes >= status.kmin) return "ecn-ramp";
	return "below-kmin";
}

void MaybeRefreshStatusSnapshot(NodeContainer* nodes, Time stopTime, bool force) {
	const auto nowWall = std::chrono::steady_clock::now();
	if (!status_wall_clock_ready) return;
	if (!force && nowWall - status_last_snapshot_wall < std::chrono::seconds(1)) return;
	status_last_snapshot_wall = nowWall;

	const auto elapsedWall =
	    std::chrono::duration_cast<std::chrono::seconds>(nowWall - status_start_wall).count();
	const FlowStatus flows = CollectFlowStatus(nodes);
	const BottleneckStatus bottleneck = CollectBottleneckStatus(nodes);
	const double simNowSeconds = Simulator::Now().GetSeconds();
	const double simStopSeconds = stopTime.GetSeconds();
	const double simPercent = simStopSeconds > 0.0
	                              ? std::min(100.0, 100.0 * simNowSeconds / simStopSeconds)
	                              : 100.0;
	const std::string wallText = FormatWallDuration(static_cast<uint64_t>(elapsedWall));
	const std::string etaText = FormatRemainingWallTime(simNowSeconds,
	                                                    simStopSeconds,
	                                                    static_cast<uint64_t>(elapsedWall));
	const double sharedPct = bottleneck.bufferBytes > 0
	                             ? 100.0 * bottleneck.sharedBufferBytes / bottleneck.bufferBytes
	                             : 0.0;
	std::string line = fmt::format(
	    "HPCC status wall={} sim={:.6f}/{:.6f}s ({:.2f}%) eta={} events={} "
	    "flows active={} qps={} started={}/{} completed={} pending={} "
	    "bytes_left={} in_flight={} ",
	    wallText,
	    simNowSeconds,
	    simStopSeconds,
	    simPercent,
	    etaText,
	    Simulator::GetEventCount(),
	    flows.active,
	    flows.activeQps,
	    flows.started,
	    flow_num,
	    flows.completed,
	    flows.pending,
	    flows.bytesLeft,
	    flows.bytesInFlight);

	if (bottleneck.found) {
		line += fmt::format(
		    "bottleneck sw={} port={} pg={} q={}B kmin={} kmax={} "
		    "ratio={:.2f} state={} pfc_thr={} paused_q={} ecn_q={} "
		    "shared={}B/{:.2f}% total_egress={}B",
		    bottleneck.switchId,
		    bottleneck.port,
		    bottleneck.pg,
		    bottleneck.queueBytes,
		    bottleneck.kmin,
		    bottleneck.kmax,
		    bottleneck.kmaxRatio,
		    GetBottleneckState(bottleneck),
		    bottleneck.pfcThreshold,
		    bottleneck.pausedQueues,
		    bottleneck.ecnQueues,
		    bottleneck.sharedBufferBytes,
		    sharedPct,
		    bottleneck.totalEgressBytes);
	} else {
		line += "bottleneck none";
	}

	std::lock_guard<std::mutex> lock(status_snapshot_mutex);
	status_snapshot = std::move(line);
}

void PrintStatusSnapshot() {
	std::string snapshot;
	{
		std::lock_guard<std::mutex> lock(status_snapshot_mutex);
		snapshot = status_snapshot;
	}
	if (!snapshot.empty()) {
		fmt::print(stderr, "\n{}\n", snapshot);
		std::fflush(stderr);
	}
}

void StatusPrinterLoop() {
	std::unique_lock<std::mutex> lock(status_thread_mutex);
	while (status_thread_running.load()) {
		if (status_thread_cv.wait_for(lock, std::chrono::seconds(5), [] {
			    return !status_thread_running.load();
		    })) {
			break;
		}
		PrintStatusSnapshot();
	}
}

void PrintSimulationStatus(NodeContainer* nodes, Time stopTime, Time pollInterval, bool force) {
	MaybeRefreshStatusSnapshot(nodes, stopTime, force);
	if (force) PrintStatusSnapshot();

	if (Simulator::Now() + pollInterval < stopTime) {
		Simulator::Schedule(pollInterval, &PrintSimulationStatus, nodes, stopTime, pollInterval, false);
	}
}

void CalculateRoute(Ptr<Node> host) {
	vector<Ptr<Node> > q;
	map<Ptr<Node>, int> dis;
	map<Ptr<Node>, uint64_t> delay;
	map<Ptr<Node>, uint64_t> txDelay;
	map<Ptr<Node>, uint64_t> bw;
	q.push_back(host);
	dis[host] = 0; delay[host] = 0; txDelay[host] = 0;
	bw[host] = 0xfffffffffffffffflu;
	for (int i = 0; i < (int)q.size(); i++) {
		Ptr<Node> now = q[i];
		int d = dis[now];
		for (auto it = nbr2if[now].begin(); it != nbr2if[now].end(); it++) {
			if (!it->second.up) continue;
			Ptr<Node> next = it->first;
			if (dis.find(next) == dis.end()) {
				dis[next] = d + 1;
				delay[next] = delay[now] + it->second.delay;
				txDelay[next] = txDelay[now] + packet_payload_size * 1000000000lu * 8 / it->second.bw;
				bw[next] = std::min(bw[now], it->second.bw);
				if (next->GetNodeType() == 1) q.push_back(next);
			}
			if (d + 1 == dis[next]) nextHop[next][host].push_back(now);
		}
	}
	for (auto it : delay) pairDelay[it.first][host] = it.second;
	for (auto it : txDelay) pairTxDelay[it.first][host] = it.second;
	for (auto it : bw) pairBw[it.first->GetId()][host->GetId()] = it.second;
}

void CalculateRoutes(NodeContainer& n) {
	for (int i = 0; i < (int)n.GetN(); i++) {
		Ptr<Node> node = n.Get(i);
		if (node->GetNodeType() == 0) CalculateRoute(node);
	}
}

void SetRoutingEntries() {
	for (auto i = nextHop.begin(); i != nextHop.end(); i++) {
		Ptr<Node> node = i->first;
		auto& table = i->second;
		for (auto j = table.begin(); j != table.end(); j++) {
			Ptr<Node> dst = j->first;
			Ipv4Address dstAddr = dst->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
			vector<Ptr<Node> > nexts = j->second;
			for (int k = 0; k < (int)nexts.size(); k++) {
				Ptr<Node> next = nexts[k];
				uint32_t interface = nbr2if[node][next].idx;
				if (node->GetNodeType() == 1)
					DynamicCast<SwitchNode>(node)->AddTableEntry(dstAddr, interface);
				else
					node->GetObject<RdmaDriver>()->m_rdma->AddTableEntry(dstAddr, interface);
			}
		}
	}
}

void TakeDownLink(NodeContainer n, Ptr<Node> a, Ptr<Node> b) {
	if (!nbr2if[a][b].up) return;
	nbr2if[a][b].up = nbr2if[b][a].up = false;
	nextHop.clear();
	CalculateRoutes(n);
	for (uint32_t i = 0; i < n.GetN(); i++) {
		if (n.Get(i)->GetNodeType() == 1)
			DynamicCast<SwitchNode>(n.Get(i))->ClearTable();
		else
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->ClearTable();
	}
	DynamicCast<QbbNetDevice>(a->GetDevice(nbr2if[a][b].idx))->TakeDown();
	DynamicCast<QbbNetDevice>(b->GetDevice(nbr2if[b][a].idx))->TakeDown();
	SetRoutingEntries();
	for (uint32_t i = 0; i < n.GetN(); i++) {
		if (n.Get(i)->GetNodeType() == 0)
			n.Get(i)->GetObject<RdmaDriver>()->m_rdma->RedistributeQp();
	}
}

uint64_t get_nic_rate(NodeContainer& n) {
	for (uint32_t i = 0; i < n.GetN(); i++)
		if (n.Get(i)->GetNodeType() == 0)
			return DynamicCast<QbbNetDevice>(n.Get(i)->GetDevice(1))->GetDataRate().GetBitRate();
	return 0;
}

/************************************************
 * Main
 ***********************************************/
int main(int argc, char* argv[])
{
	clock_t begint, endt;
	begint = clock();

	if (argc <= 1) {
		fmt::print(stderr, "Error: require a YAML config file\n");
		return 1;
	}

	// ── Step 1: Load config from YAML ──────────────────────────────
	HpccConfig cfg(argv[1]);
	cfg.print();

	// Populate globals used by helper functions
	packet_payload_size = cfg.get_packet_payload_size();
	has_win = cfg.get_has_win();
	global_t = cfg.get_global_t();
	fs_disable_window = cfg.get_fs_disable_window();
	qlen_dump_interval = cfg.get_qlen_dump_interval();
	qlen_mon_interval = cfg.get_qlen_mon_interval();
	qlen_mon_start_ns = cfg.get_qlen_mon_start();
	qlen_mon_end_ns = cfg.get_qlen_mon_end();

	// ── Step 2: ns3 defaults ───────────────────────────────────────
	bool dynamicth = cfg.get_use_dynamic_pfc_threshold();
	Config::SetDefault("ns3::QbbNetDevice::PauseTime", UintegerValue(cfg.get_pause_time()));
	Config::SetDefault("ns3::QbbNetDevice::QcnEnabled", BooleanValue(cfg.get_enable_qcn()));
	Config::SetDefault("ns3::QbbNetDevice::DynamicThreshold", BooleanValue(dynamicth));

	// IntHop / IntHeader mode
	IntHop::multi = cfg.get_int_multi();
	uint32_t cc_mode = cfg.get_cc_mode();
	if (cc_mode == 7)
		IntHeader::mode = IntHeader::TS;
	else if (cc_mode == 3)
		IntHeader::mode = IntHeader::NORMAL;
	else if (cc_mode == 10)
		IntHeader::mode = IntHeader::PINT;
	else if (cc_mode == 11)
		IntHeader::mode = IntHeader::FS;   // HPCC-FS: single RCP-style fair-rate field
	else
		IntHeader::mode = IntHeader::NONE;

	// Pint setup
	if (cc_mode == 10) {
		Pint::set_log_base(cfg.get_pint_log_base());
		IntHeader::pint_bytes = Pint::get_n_bytes();
		fmt::print("PINT bits: {} bytes: {}\n", Pint::get_n_bits(), Pint::get_n_bytes());
	}

	// ── Step 3: Open topology / flow / trace files ─────────────────
	topof.open(cfg.get_topology_file().c_str());
	if (!topof.is_open()) {
		fmt::print(stderr, "ERROR: Cannot open topology file: {}\n", cfg.get_topology_file());
		return 1;
	}
	flowf.open(cfg.get_flow_file().c_str());
	if (!flowf.is_open()) {
		fmt::print(stderr, "ERROR: Cannot open flow file: {}\n", cfg.get_flow_file());
		return 1;
	}
	tracef.open(cfg.get_trace_file().c_str());
	if (!tracef.is_open()) {
		fmt::print(stderr, "ERROR: Cannot open trace file: {}\n", cfg.get_trace_file());
		return 1;
	}

	uint32_t node_num = 0, switch_num = 0, link_num = 0, trace_num = 0;
	topof >> node_num; strip_cr(topof);
	topof >> switch_num; strip_cr(topof);
	topof >> link_num; strip_cr(topof);
	flowf >> flow_num; strip_cr(flowf);
	tracef >> trace_num; strip_cr(tracef);

	// Validate parsed header values
	if (flowf.fail()) {
		fmt::print(stderr, "ERROR: Invalid flow count header in flow file: {}\n", cfg.get_flow_file());
		return 1;
	}
	if (node_num == 0 || node_num > 100000) {
		fmt::print(stderr, "ERROR: Invalid node_num={} from topology file (CRLF issue?)\n", node_num);
		return 1;
	}
	if (link_num == 0 || link_num > 1000000) {
		fmt::print(stderr, "ERROR: Invalid link_num={} from topology file (CRLF issue?)\n", link_num);
		return 1;
	}
	if (switch_num > node_num) {
		fmt::print(stderr, "ERROR: switch_num={} > node_num={} — topology corrupted\n", switch_num, node_num);
		return 1;
	}
	if (!ValidateFlowFile(cfg.get_flow_file(), flow_num, node_num)) {
		return 1;
	}

	fmt::print("\n{:=^60}\n", " Topology ");
	fmt::print("{:<30} {}\n", "Nodes", node_num);
	fmt::print("{:<30} {}\n", "Switches", switch_num);
	fmt::print("{:<30} {}\n", "Links", link_num);
	fmt::print("{:<30} {}\n", "Flows", flow_num);
	fmt::print("{:<30} {}\n", "Trace nodes", trace_num);

	// ── Step 4: Create nodes ───────────────────────────────────────
	std::vector<uint32_t> node_type(node_num, 0);
	for (uint32_t i = 0; i < switch_num; i++) {
		uint32_t sid;
		topof >> sid; strip_cr(topof);
		if (sid >= node_num) {
			fmt::print(stderr, "ERROR: Switch id {} >= node_num {} at switch index {}\n", sid, node_num, i);
			return 1;
		}
		node_type[sid] = 1;
	}
	for (uint32_t i = 0; i < node_num; i++) {
		if (node_type[i] == 0) {
			n.Add(CreateObject<Node>());
		} else {
			Ptr<SwitchNode> sw = CreateObject<SwitchNode>();
			n.Add(sw);
			sw->SetAttribute("EcnEnabled", BooleanValue(cfg.get_enable_qcn()));
		}
	}
	NS_LOG_INFO("Create nodes.");

	// ── Step 5: Install internet stack ─────────────────────────────
	InternetStackHelper internet;
	internet.Install(n);

	// Assign IP to each server
	for (uint32_t i = 0; i < node_num; i++) {
		if (n.Get(i)->GetNodeType() == 0) {
			serverAddress.resize(i + 1);
			serverAddress[i] = node_id_to_ip(i);
		}
	}
	NS_LOG_INFO("Create channels.");

	// ── Step 6: Create links / channels ────────────────────────────
	Ptr<RateErrorModel> rem = CreateObject<RateErrorModel>();
	Ptr<UniformRandomVariable> uv = CreateObject<UniformRandomVariable>();
	rem->SetRandomVariable(uv);
	uv->SetStream(50);
	rem->SetAttribute("ErrorRate", DoubleValue(cfg.get_error_rate_per_link()));
	rem->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));

	FILE* pfc_file = fopen(cfg.get_pfc_output_file().c_str(), "w");

	QbbHelper qbb;
	Ipv4AddressHelper ipv4;
	for (uint32_t i = 0; i < link_num; i++) {
		uint32_t src, dst;
		std::string data_rate, link_delay;
		double error_rate;
		topof >> src >> dst >> data_rate >> link_delay >> error_rate;
		strip_cr(topof);

		if (topof.fail()) {
			fmt::print(stderr, "ERROR: Failed to parse link {} (bad format or CRLF issue)\n", i);
			return 1;
		}
		if (src >= node_num || dst >= node_num) {
			fmt::print(stderr, "ERROR: Link {} has src={} dst={} but node_num={}\n", i, src, dst, node_num);
			return 1;
		}
		if (data_rate.empty() || link_delay.empty()) {
			fmt::print(stderr, "ERROR: Link {} has empty data_rate or link_delay\n", i);
			return 1;
		}

		Ptr<Node> snode = n.Get(src), dnode = n.Get(dst);
		qbb.SetDeviceAttribute("DataRate", StringValue(data_rate));
		qbb.SetChannelAttribute("Delay", StringValue(link_delay));

		if (error_rate > 0) {
			Ptr<RateErrorModel> rem2 = CreateObject<RateErrorModel>();
			Ptr<UniformRandomVariable> uv2 = CreateObject<UniformRandomVariable>();
			rem2->SetRandomVariable(uv2);
			uv2->SetStream(50);
			rem2->SetAttribute("ErrorRate", DoubleValue(error_rate));
			rem2->SetAttribute("ErrorUnit", StringValue("ERROR_UNIT_PACKET"));
			qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem2));
		} else {
			qbb.SetDeviceAttribute("ReceiveErrorModel", PointerValue(rem));
		}
		fflush(stdout);

		NetDeviceContainer d = qbb.Install(snode, dnode);
		if (snode->GetNodeType() == 0) {
			Ptr<Ipv4> ipv4_s = snode->GetObject<Ipv4>();
			ipv4_s->AddInterface(d.Get(0));
			ipv4_s->AddAddress(1, Ipv4InterfaceAddress(serverAddress[src], Ipv4Mask(0xff000000)));
		}
		if (dnode->GetNodeType() == 0) {
			Ptr<Ipv4> ipv4_d = dnode->GetObject<Ipv4>();
			ipv4_d->AddInterface(d.Get(1));
			ipv4_d->AddAddress(1, Ipv4InterfaceAddress(serverAddress[dst], Ipv4Mask(0xff000000)));
		}

		nbr2if[snode][dnode].idx = DynamicCast<QbbNetDevice>(d.Get(0))->GetIfIndex();
		nbr2if[snode][dnode].up = true;
		nbr2if[snode][dnode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(0))->GetChannel())->GetDelay().GetTimeStep();
		nbr2if[snode][dnode].bw = DynamicCast<QbbNetDevice>(d.Get(0))->GetDataRate().GetBitRate();
		nbr2if[dnode][snode].idx = DynamicCast<QbbNetDevice>(d.Get(1))->GetIfIndex();
		nbr2if[dnode][snode].up = true;
		nbr2if[dnode][snode].delay = DynamicCast<QbbChannel>(DynamicCast<QbbNetDevice>(d.Get(1))->GetChannel())->GetDelay().GetTimeStep();
		nbr2if[dnode][snode].bw = DynamicCast<QbbNetDevice>(d.Get(1))->GetDataRate().GetBitRate();

		char ipstring[16];
		sprintf(ipstring, "10.%d.%d.0", i / 254 + 1, i % 254 + 1);
		ipv4.SetBase(ipstring, "255.255.255.0");
		ipv4.Assign(d);

		DynamicCast<QbbNetDevice>(d.Get(0))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback(&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(0))));
		DynamicCast<QbbNetDevice>(d.Get(1))->TraceConnectWithoutContext("QbbPfc", MakeBoundCallback(&get_pfc, pfc_file, DynamicCast<QbbNetDevice>(d.Get(1))));
	}

	nic_rate = get_nic_rate(n);

	// ── Step 7: Configure switches (ECN, PFC, buffer) ──────────────
	auto& kmin_map = cfg.get_kmin_map();
	auto& kmax_map = cfg.get_kmax_map();
	auto& pmax_map = cfg.get_pmax_map();

	for (uint32_t i = 0; i < node_num; i++) {
		if (n.Get(i)->GetNodeType() == 1) {
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
			uint32_t shift = 3;
			for (uint32_t j = 1; j < sw->GetNDevices(); j++) {
				Ptr<QbbNetDevice> dev = DynamicCast<QbbNetDevice>(sw->GetDevice(j));
				uint64_t rate = dev->GetDataRate().GetBitRate();
				NS_ASSERT_MSG(kmin_map.find(rate) != kmin_map.end(), "must set kmin for each link speed");
				NS_ASSERT_MSG(kmax_map.find(rate) != kmax_map.end(), "must set kmax for each link speed");
				NS_ASSERT_MSG(pmax_map.find(rate) != pmax_map.end(), "must set pmax for each link speed");
				sw->m_mmu->ConfigEcn(j, kmin_map.at(rate), kmax_map.at(rate), pmax_map.at(rate));
				uint64_t delay = DynamicCast<QbbChannel>(dev->GetChannel())->GetDelay().GetTimeStep();
				uint32_t headroom = rate * delay / 8 / 1000000000 * 3;
				sw->m_mmu->ConfigHdrm(j, headroom);
				sw->m_mmu->pfc_a_shift[j] = shift;
				while (rate > nic_rate && sw->m_mmu->pfc_a_shift[j] > 0) {
					sw->m_mmu->pfc_a_shift[j]--;
					rate /= 2;
				}
			}
			sw->m_mmu->ConfigNPort(sw->GetNDevices() - 1);
			sw->m_mmu->ConfigBufferSize(cfg.get_buffer_size() * 1024 * 1024);
			sw->m_mmu->node_id = sw->GetId();
		}
	}

	// ── Step 8: Install RDMA driver on servers ─────────────────────
	#define ENABLE_QP 1
	#if ENABLE_QP
	FILE* fct_output = fopen(cfg.get_fct_output_file().c_str(), "w");
	for (uint32_t i = 0; i < node_num; i++) {
		if (n.Get(i)->GetNodeType() == 0) {
			Ptr<RdmaHw> rdmaHw = CreateObject<RdmaHw>();
			rdmaHw->SetAttribute("ClampTargetRate", BooleanValue(cfg.get_clamp_target_rate()));
			rdmaHw->SetAttribute("AlphaResumInterval", DoubleValue(cfg.get_alpha_resume_interval()));
			rdmaHw->SetAttribute("RPTimer", DoubleValue(cfg.get_rp_timer()));
			rdmaHw->SetAttribute("FastRecoveryTimes", UintegerValue(cfg.get_fast_recovery_times()));
			rdmaHw->SetAttribute("EwmaGain", DoubleValue(cfg.get_ewma_gain()));
			rdmaHw->SetAttribute("RateAI", DataRateValue(DataRate(cfg.get_rate_ai())));
			rdmaHw->SetAttribute("RateHAI", DataRateValue(DataRate(cfg.get_rate_hai())));
			rdmaHw->SetAttribute("L2BackToZero", BooleanValue(cfg.get_l2_back_to_zero()));
			rdmaHw->SetAttribute("L2ChunkSize", UintegerValue(cfg.get_l2_chunk_size()));
			rdmaHw->SetAttribute("L2AckInterval", UintegerValue(cfg.get_l2_ack_interval()));
			rdmaHw->SetAttribute("CcMode", UintegerValue(cc_mode));
			rdmaHw->SetAttribute("RateDecreaseInterval", DoubleValue(cfg.get_rate_decrease_interval()));
			rdmaHw->SetAttribute("MinRate", DataRateValue(DataRate(cfg.get_min_rate())));
			rdmaHw->SetAttribute("Mtu", UintegerValue(packet_payload_size));
			rdmaHw->SetAttribute("MiThresh", UintegerValue(cfg.get_mi_thresh()));
			rdmaHw->SetAttribute("VarWin", BooleanValue(cfg.get_var_win()));
			rdmaHw->SetAttribute("FastReact", BooleanValue(cfg.get_fast_react()));
			rdmaHw->SetAttribute("MultiRate", BooleanValue(cfg.get_multi_rate()));
			rdmaHw->SetAttribute("SampleFeedback", BooleanValue(cfg.get_sample_feedback()));
			rdmaHw->SetAttribute("MbMode", UintegerValue(cfg.get_mb_mode()));
			rdmaHw->SetAttribute("MbGamma", DoubleValue(cfg.get_mb_gamma()));
			rdmaHw->SetAttribute("TargetUtil", DoubleValue(cfg.get_u_target()));
			rdmaHw->SetAttribute("RateBound", BooleanValue(cfg.get_rate_bound()));
			rdmaHw->SetAttribute("DctcpRateAI", DataRateValue(DataRate(cfg.get_dctcp_rate_ai())));
			rdmaHw->SetPintSmplThresh(cfg.get_pint_prob());

			Ptr<RdmaDriver> rdma = CreateObject<RdmaDriver>();
			Ptr<Node> node = n.Get(i);
			rdma->SetNode(node);
			rdma->SetRdmaHw(rdmaHw);
			node->AggregateObject(rdma);
			rdma->Init();
			rdma->TraceConnectWithoutContext("QpComplete", MakeBoundCallback(qp_finish, fct_output));
		}
	}
	#endif

	// ── Step 9: ACK priority ───────────────────────────────────────
	if (cfg.get_ack_high_prio())
		RdmaEgressQueue::ack_q_idx = 0;
	else
		RdmaEgressQueue::ack_q_idx = 3;

	// ── Step 10: Routing ───────────────────────────────────────────
	CalculateRoutes(n);
	SetRoutingEntries();

	// ── Step 11: BDP and delay ─────────────────────────────────────
	maxRtt = maxBdp = 0;
	for (uint32_t i = 0; i < node_num; i++) {
		if (n.Get(i)->GetNodeType() != 0) continue;
		for (uint32_t j = 0; j < node_num; j++) {
			if (n.Get(j)->GetNodeType() != 0) continue;
			uint64_t delay = pairDelay[n.Get(i)][n.Get(j)];
			uint64_t txDelay = pairTxDelay[n.Get(i)][n.Get(j)];
			uint64_t rtt = delay * 2 + txDelay;
			uint64_t bw = pairBw[i][j];
			uint64_t bdp = rtt * bw / 1000000000 / 8;
			pairBdp[n.Get(i)][n.Get(j)] = bdp;
			pairRtt[i][j] = rtt;
			if (bdp > maxBdp) maxBdp = bdp;
			if (rtt > maxRtt) maxRtt = rtt;
		}
	}
	fmt::print("\n{:=^60}\n", " BDP / RTT ");
	fmt::print("{:<30} {}\n", "maxRtt", maxRtt);
	fmt::print("{:<30} {}\n", "maxBdp", maxBdp);

	// ── Step 12: Switch CC mode ────────────────────────────────────
	for (uint32_t i = 0; i < node_num; i++) {
		if (n.Get(i)->GetNodeType() == 1) {
			Ptr<SwitchNode> sw = DynamicCast<SwitchNode>(n.Get(i));
			sw->SetAttribute("CcMode", UintegerValue(cc_mode));
			sw->SetAttribute("MaxRtt", UintegerValue(maxRtt));
			sw->SetAttribute("FsAlpha", DoubleValue(cfg.get_fs_alpha()));
			sw->SetAttribute("FsBeta", DoubleValue(cfg.get_fs_beta()));
			sw->SetAttribute("FsInitFrac", DoubleValue(cfg.get_fs_init_frac()));
		}
	}

	// ── Step 13: Trace setup ───────────────────────────────────────
	NodeContainer trace_nodes;
	for (uint32_t i = 0; i < trace_num; i++) {
		uint32_t nid;
		tracef >> nid;
		if (nid >= n.GetN()) continue;
		trace_nodes = NodeContainer(trace_nodes, n.Get(nid));
	}

	std::string trace_output_file = cfg.get_trace_output_file();
	FILE* trace_output = fopen(trace_output_file.c_str(), "w");
	if (cfg.get_enable_trace())
		qbb.EnableTracing(trace_output, trace_nodes);

	// Dump link speed to trace file
	{
		SimSetting sim_setting;
		for (auto i : nbr2if) {
			for (auto j : i.second) {
				uint16_t node = i.first->GetId();
				uint8_t intf = j.second.idx;
				uint64_t bps = DynamicCast<QbbNetDevice>(i.first->GetDevice(j.second.idx))->GetDataRate().GetBitRate();
				sim_setting.port_speed[node][intf] = bps;
			}
		}
		sim_setting.win = maxBdp;
		sim_setting.Serialize(trace_output);
	}

	Ipv4GlobalRoutingHelper::PopulateRoutingTables();
	NS_LOG_INFO("Create Applications.");

	// ── Step 14: Flow scheduling ───────────────────────────────────
	Time interPacketInterval = Seconds(0.0000005 / 2);

	// Maintain port number for each host pair
	for (uint32_t i = 0; i < node_num; i++) {
		if (n.Get(i)->GetNodeType() == 0)
			for (uint32_t j = 0; j < node_num; j++) {
				if (n.Get(j)->GetNodeType() == 0)
					portNumder[i][j] = 10000;
			}
	}

	flow_input.idx = 0;
	if (flow_num > 0) {
		ReadFlowInput();
		Simulator::Schedule(Seconds(flow_input.start_time) - Simulator::Now(), ScheduleFlowInputs);
	}

	topof.close();
	tracef.close();

	// ── Step 15: Link down scheduling ──────────────────────────────
	auto& ld = cfg.get_link_down();
	if (ld.time > 0) {
		Simulator::Schedule(Seconds(2) + MicroSeconds(ld.time),
		                    &TakeDownLink, n, n.Get(ld.from_node), n.Get(ld.to_node));
	}

	// ── Step 16: Buffer monitor ────────────────────────────────────
	FILE* qlen_output = fopen(cfg.get_qlen_mon_file().c_str(), "w");
	FILE* bottleneck_output = fopen(cfg.get_bottleneck_output_file().c_str(), "w");
	Simulator::Schedule(NanoSeconds(qlen_mon_start_ns), &monitor_buffer, qlen_output, &n);

	// ── Step 17: Run simulation ────────────────────────────────────
	fmt::print("\n{:=^60}\n", " Running Simulation ");
	fflush(stdout);
	NS_LOG_INFO("Run Simulation.");
	Time stopTime = Seconds(cfg.get_simulator_stop_time());
	Time statusPollInterval = MilliSeconds(10);
	status_stop_time = stopTime;
	status_start_wall = std::chrono::steady_clock::now();
	status_last_snapshot_wall = status_start_wall - std::chrono::seconds(1);
	{
		std::lock_guard<std::mutex> lock(status_snapshot_mutex);
		status_snapshot.clear();
	}
	status_wall_clock_ready = true;
	status_thread_running.store(true);
	status_thread = std::thread(&StatusPrinterLoop);
	Simulator::Stop(stopTime);
	Simulator::ScheduleNow(&PrintSimulationStatus, &n, stopTime, statusPollInterval, true);
	Simulator::ScheduleNow(&PrintProgressBar, stopTime, Seconds(1));
	Simulator::Run();
	status_thread_running.store(false);
	status_thread_cv.notify_all();
	if (status_thread.joinable()) status_thread.join();
	PrintSimulationStatus(&n, stopTime, statusPollInterval, true);
	PrintProgressBar(stopTime, Seconds(1));
	fmt::print(stderr, "\n");
	write_bottleneck_summary(bottleneck_output);
	Simulator::Destroy();
	NS_LOG_INFO("Done.");
	fclose(trace_output);
	fclose(qlen_output);
	fclose(bottleneck_output);

	endt = clock();
	fmt::print("\n{:=^60}\n", " Simulation Complete ");
	fmt::print("Elapsed: {:.4f}s\n", (double)(endt - begint) / CLOCKS_PER_SEC);

	return 0;
}
