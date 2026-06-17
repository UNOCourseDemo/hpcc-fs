/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
* Copyright (c) 2006 Georgia Tech Research Corporation, INRIA
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License version 2 as
* published by the Free Software Foundation;
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*
* Author: Yuliang Li <yuliangli@g.harvard.com>
*/

#define __STDC_LIMIT_MACROS 1
#include <stdint.h>
#include <stdio.h>
#include "ns3/qbb-net-device.h"
#include "ns3/log.h"
#include "ns3/boolean.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "ns3/data-rate.h"
#include "ns3/object-vector.h"
#include "ns3/pause-header.h"
#include "ns3/drop-tail-queue.h"
#include "ns3/assert.h"
#include "ns3/ipv4.h"
#include "ns3/ipv4-header.h"
#include "ns3/simulator.h"
#include "ns3/point-to-point-channel.h"
#include "ns3/qbb-channel.h"
#include "ns3/random-variable-stream.h"
#include "ns3/flow-id-tag.h"
#include "ns3/qbb-header.h"
#include "ns3/error-model.h"
#include "ns3/cn-header.h"
#include "ns3/ppp-header.h"
#include "ns3/udp-header.h"
#include "ns3/seq-ts-header.h"
#include "ns3/pointer.h"
#include "ns3/custom-header.h"
#include "ns3/old-drop-tail-queue.h"

#include <iostream>

NS_LOG_COMPONENT_DEFINE("QbbNetDevice");

namespace ns3 {
	
	uint32_t RdmaEgressQueue::ack_q_idx = 3;
	// RdmaEgressQueue
	TypeId RdmaEgressQueue::GetTypeId (void)
	{
		static TypeId tid = TypeId ("ns3::RdmaEgressQueue")
			.SetParent<Object> ()
			.AddTraceSource ("RdmaEnqueue", "Enqueue a packet in the RdmaEgressQueue.",
					MakeTraceSourceAccessor (&RdmaEgressQueue::m_traceRdmaEnqueue),
                                            "ns3::BEgressQueue::PacketTracedCallback")
			.AddTraceSource ("RdmaDequeue", "Dequeue a packet in the RdmaEgressQueue.",
					MakeTraceSourceAccessor (&RdmaEgressQueue::m_traceRdmaDequeue),
                                            "ns3::BEgressQueue::PacketTracedCallback")
			;
		return tid;
	}

	RdmaEgressQueue::RdmaEgressQueue(){
		m_rrlast = 0;
		m_qlast = 0;
		m_ackQ = CreateObject<OldDropTailQueue>();
		m_ackQ->SetAttribute("MaxBytes", UintegerValue(0xffffffff)); // queue limit is on a higher level, not here
	}

	Ptr<Packet> RdmaEgressQueue::DequeueQindex(int qIndex){
		if (qIndex == -1){ // high prio
			Ptr<Packet> p = m_ackQ->Dequeue();
			m_qlast = -1;
			m_traceRdmaDequeue(p, 0);
			return p;
		}
		if (qIndex >= 0){ // qp
			Ptr<Packet> p = m_rdmaGetNxtPkt(m_qpGrp->Get(qIndex));
			m_rrlast = qIndex;
			m_qlast = qIndex;
			m_traceRdmaDequeue(p, m_qpGrp->Get(qIndex)->m_pg);
//            NS_LOG_UNCOND(
//                "Haoyu: +2+++ RdmaEgressQueue DequeueQindex: dequeued packet from QP (dip: " << m_qpGrp->Get(qIndex)->dip
//                          << ", sip: " << m_qpGrp->Get(qIndex)->sip
//                          << ", sport: " << m_qpGrp->Get(qIndex)->sport
//                          << ", dport: " << m_qpGrp->Get(qIndex)->dport
//                          << ", pg: " << m_qpGrp->Get(qIndex)->m_pg << ")"
//            );
            CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
            ch.getInt = 1; // parse INT header
            p->PeekHeader(ch);
//            NS_LOG_UNCOND(
//                "Haoyu: +2+++ RdmaEgressQueue DequeueQindex: dequeued packet from QP (dip: " << m_qpGrp->Get(qIndex)->dip <<
//                ", size: " << p->GetSize() <<
//                ", sip: " << ch.sip <<
//                ", dip: " << ch.dip <<
//                ", sport: " << ch.udp.sport <<
//                ", dport: " << ch.udp.dport <<
//                ", pg: " << ch.udp.pg
//            );

			return p;
		}
		return 0;
	}
    /***
     * Get the next queue to send
     * @param paused
     * @return
     */
	int RdmaEgressQueue::GetNextQindex(bool paused[]){
        // "paused[]" is indexed by Priority Group (PG). If paused[pg] is true,
        // that PG is currently PFC-paused and *must not* transmit.
        //
        // This function selects *what to send next* by returning:
        //   -1   : send from the high-priority ACK/control queue (m_ackQ)
        //   >=0  : send from RDMA QP group at that index
        //   -2   : send from TCP/IP queue (non-RDMA traffic)
        //   -1024: no eligible packet found
		bool found = false;
		uint32_t qIndex;

        // ---------------------------------------------------------------------
        // 1) Highest priority: ACK/control queue (a dedicated high-priority queue)
        // ---------------------------------------------------------------------
        // Only serve it if:
        //   - the ACK priority group isn't paused, AND
        //   - there is at least one packet waiting in m_ackQ
        //
        // In this codebase, "ack_q_idx" is the PG used for ACK/control traffic.
		if (!paused[ack_q_idx] && m_ackQ->GetNPackets() > 0)
            // Return -1 to indicate: "dequeue from m_ackQ" (handled by DequeueQindex).
			return -1;

		// no pkt in the highest priority queue, do rr for each qp
        // ---------------------------------------------------------------------
        // 2) No ACKs: do round-robin among active RDMA queue pairs (QPs)
        //    with a small alternation trick: sometimes check TCP/IP too.
        // ---------------------------------------------------------------------
        // This loop runs twice at most (dorr = 0,1). In each iteration, it bumps
        // a global/outer counter "hostDequeueIndex" and:
        //   - on odd hostDequeueIndex: try RDMA QPs (round-robin)
        //   - on even hostDequeueIndex: try TCP/IP queue
        //
        // Net effect: it interleaves RDMA and TCP/IP service opportunities.

        // ---- 2) Otherwise, pick among RDMA QPs (and optionally TCP/IP) ----
        // This "no ACKs ready" case does round-robin selection across active QPs,
        // skipping:
        //   - paused priority groups
        //   - QPs with no bytes left
        //   - QPs that are window-bound (cannot send due to flow-control window)
        //   - QPs that are rate-limited until some future time (m_nextAvail)
        //
        // res is initialized to a sentinel meaning "nothing found".
		int res = -1024;

        // fcount is the number of currently-tracked (active) QPs.
		uint32_t fcount = m_qpGrp->GetN();
        // Track the smallest index where we saw a finished QP.
        // The code later compacts the QP array starting from that point.
		uint32_t min_finish_id = 0xffffffff;
        // Iterate through ALL QPs in round-robin order, starting just after m_rrlast.
        // qIndex goes 1..fcount inclusive so we check fcount candidates.
		for (qIndex = 1; qIndex <= fcount; qIndex++){
            // Round-robin mapping:
            // - m_rrlast remembers the last QP index that successfully sent.
            // - we start from (m_rrlast + 1) and wrap around.
			uint32_t idx = (qIndex + m_rrlast) % fcount;
			Ptr<RdmaQueuePair> qp = m_qpGrp->Get(idx);
            // Eligibility checks:
            //  (1) priority group of this QP is not paused (PFC)
            //  (2) it still has data to send
            //  (3) it is not window-bound (can't send because send window is closed)
			if (!paused[qp->m_pg] && qp->GetBytesLeft() > 0 && !qp->IsWinBound()){
                // Rate pacing / availability gate:
                // If the QP isn't allowed to send until a future time, skip it.
				if (m_qpGrp->Get(idx)->m_nextAvail.GetTimeStep() > Simulator::Now().GetTimeStep()) //not available now
					continue;
                // Found an eligible QP to serve next.
				res = idx;
				break;
			}else if (qp->IsFinished()){
                // If the QP is finished, remember the earliest finished index.
                // Later we will compact the QP list to remove finished entries.
				min_finish_id = idx < min_finish_id ? idx : min_finish_id;
			}
		}

		// clear the finished qp

        // ---- 3) Opportunistically remove finished QPs (list compaction) ----
        // If we observed at least one finished QP, shrink the QP vector by
        // moving non-finished QPs down, starting at min_finish_id.
        //
        // This is an O(n) in-place compaction to keep m_qpGrp small and
        // avoid scanning dead QPs forever.
		if (min_finish_id < 0xffffffff){
			int nxt = min_finish_id;
            // Direct access to the underlying vector used by m_qpGrp.
            // (This is an implementation detail of this particular codebase.)
			auto &qps = m_qpGrp->m_qps;
			for (int i = min_finish_id + 1; i < fcount; i++) if (!qps[i]->IsFinished()){
                // If the QP we selected (res) gets shifted due to compaction,
                // update res to the new index (nxt).
				if (i == res) // update res to the idx after removing finished qp
					res = nxt;
                // Move surviving QP down.
				qps[nxt] = qps[i];
				nxt++;
			}
            // Physically shrink the vector to discard the tail (finished QPs).
			qps.resize(nxt);
		}
		return res;
	}

	int RdmaEgressQueue::GetLastQueue(){
		return m_qlast;
	}

	uint32_t RdmaEgressQueue::GetNBytes(uint32_t qIndex){
		NS_ASSERT_MSG(qIndex < m_qpGrp->GetN(), "RdmaEgressQueue::GetNBytes: qIndex >= m_qpGrp->GetN()");
		return m_qpGrp->Get(qIndex)->GetBytesLeft();
	}

	uint32_t RdmaEgressQueue::GetFlowCount(void){
		return m_qpGrp->GetN();
	}

	Ptr<RdmaQueuePair> RdmaEgressQueue::GetQp(uint32_t i){
		return m_qpGrp->Get(i);
	}
 
	void RdmaEgressQueue::RecoverQueue(uint32_t i){
		NS_ASSERT_MSG(i < m_qpGrp->GetN(), "RdmaEgressQueue::RecoverQueue: qIndex >= m_qpGrp->GetN()");
		m_qpGrp->Get(i)->snd_nxt = m_qpGrp->Get(i)->snd_una;
	}

	void RdmaEgressQueue::EnqueueHighPrioQ(Ptr<Packet> p){
		m_traceRdmaEnqueue(p, 0);
		m_ackQ->Enqueue(p);
	}

	void RdmaEgressQueue::CleanHighPrio(TracedCallback<Ptr<const Packet>, uint32_t> dropCb){
		while (m_ackQ->GetNPackets() > 0){
			Ptr<Packet> p = m_ackQ->Dequeue();
			dropCb(p, 0);
		}
	}

	/******************
	 * QbbNetDevice
	 *****************/
	NS_OBJECT_ENSURE_REGISTERED(QbbNetDevice);

	TypeId
		QbbNetDevice::GetTypeId(void)
	{
		static TypeId tid = TypeId("ns3::QbbNetDevice")
			.SetParent<PointToPointNetDevice>()
			.AddConstructor<QbbNetDevice>()
			.AddAttribute("QbbEnabled",
				"Enable the generation of PAUSE packet.",
				BooleanValue(true),
				MakeBooleanAccessor(&QbbNetDevice::m_qbbEnabled),
				MakeBooleanChecker())
			.AddAttribute("QcnEnabled",
				"Enable the generation of PAUSE packet.",
				BooleanValue(false),
				MakeBooleanAccessor(&QbbNetDevice::m_qcnEnabled),
				MakeBooleanChecker())
			.AddAttribute("DynamicThreshold",
				"Enable dynamic threshold.",
				BooleanValue(false),
				MakeBooleanAccessor(&QbbNetDevice::m_dynamicth),
				MakeBooleanChecker())
			.AddAttribute("PauseTime",
				"Number of microseconds to pause upon congestion",
				UintegerValue(5),
				MakeUintegerAccessor(&QbbNetDevice::m_pausetime),
				MakeUintegerChecker<uint32_t>())
			.AddAttribute ("TxBeQueue", 
					"A queue to use as the transmit queue in the device.",
					PointerValue (),
					MakePointerAccessor (&QbbNetDevice::m_queue),
					MakePointerChecker<OldQueue> ())
			.AddAttribute ("RdmaEgressQueue", 
					"A queue to use as the transmit queue in the device.",
					PointerValue (),
					MakePointerAccessor (&QbbNetDevice::m_rdmaEQ),
					MakePointerChecker<Object> ())
			.AddTraceSource ("QbbEnqueue", "Enqueue a packet in the QbbNetDevice.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceEnqueue),
                    "ns3::BEgressQueue::PacketTracedCallback")
			.AddTraceSource ("QbbDequeue", "Dequeue a packet in the QbbNetDevice.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceDequeue),
                    "ns3::BEgressQueue::PacketTracedCallback")
			.AddTraceSource ("QbbDrop", "Drop a packet in the QbbNetDevice.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceDrop),
                                                "ns3::BEgressQueue::PacketTracedCallback")
			.AddTraceSource ("RdmaQpDequeue", "A qp dequeue a packet.",
					MakeTraceSourceAccessor (&QbbNetDevice::m_traceQpDequeue),
                    "ns3::QbbNetDevice::PacketQpTracedCallback")
			.AddTraceSource ("QbbPfc", "get a PFC packet. Args: type (0 resume, 1 pause), qIndex",
					MakeTraceSourceAccessor (&QbbNetDevice::m_tracePfc),
                    "ns3::QbbNetDevice::PfcTracedCallback")
			;

		return tid;
	}

	QbbNetDevice::QbbNetDevice()
	{
		NS_LOG_FUNCTION(this);
		m_ecn_source = new std::vector<ECNAccount>;
		for (uint32_t i = 0; i < qCnt; i++){
			m_paused[i] = false;
		}

		m_rdmaEQ = CreateObject<RdmaEgressQueue>();
	}

	QbbNetDevice::~QbbNetDevice()
	{
		NS_LOG_FUNCTION(this);
	}

	void
		QbbNetDevice::DoDispose()
	{
		NS_LOG_FUNCTION(this);

		PointToPointNetDevice::DoDispose();
	}

	void
		QbbNetDevice::TransmitComplete(void)
	{
		NS_LOG_FUNCTION(this);
		NS_ASSERT_MSG(m_txMachineState == BUSY, "Must be BUSY if transmitting");
		m_txMachineState = READY;
		NS_ASSERT_MSG(m_currentPkt, "QbbNetDevice::TransmitComplete(): m_currentPkt zero");
		m_phyTxEndTrace(m_currentPkt);
		m_currentPkt = 0;
		DequeueAndTransmit();
	}

	void
		QbbNetDevice::DequeueAndTransmit(void)
	{
        // Called whenever:
        //  - a new packet is enqueued (e.g., Send(), Rdma enqueue),
        //  - the previous transmission completes (TransmitComplete()),
        //  - a paused queue is resumed (Resume()).
        //
        // Goal: if the link is up and TX is idle, pick ONE eligible packet
        // and start transmitting it (TransmitStart()).


        NS_LOG_FUNCTION(this);
        // 1) Basic guards: if link is down, or we are already transmitting, do nothing.

		if (!m_linkUp) return; // if link is down, return
		if (m_txMachineState == BUSY) return;	// Quit if channel busy
		Ptr<Packet> p;
        // 2) Different behavior depending on whether this device is a NIC (host) or a switch port.
        //    In this codebase, nodeType == 0 => host/NIC, nodeType > 0 => switch.
        if (m_node->GetNodeType() == 0){
            // =========================
            // NIC / Host-side scheduling
            // =========================
            //
            // Host uses RdmaEgressQueue to decide *what class* of traffic to send next:
            //   -1    : ACK/control high-priority queue
            //   -2    : (optional) TCP/IP device queue (some forks support this)
            //   >= 0  : RDMA Queue Pair index
            //   -1024 : nothing eligible (paused or no data or rate-limited until future)
            //
            // The selection respects:
            //  - PFC pause state per priority group (m_paused[])
            //  - per-QP pacing via qp->m_nextAvail (HPCC/DCQCN/TIMELY pacing)

            int qIndex = m_rdmaEQ->GetNextQindex(m_paused);

            if (qIndex != -1024){
				if (qIndex == -1){ // high prio
                   // 2a) High-priority ACK/control queue
					p = m_rdmaEQ->DequeueQindex(qIndex);
					m_traceDequeue(p, 0);
					TransmitStart(p);
					return;
				}
                // 2c) RDMA Queue Pair (QP) data path: qIndex >= 0
				// a qp dequeue a packet
                // Identify which QP we are serving (mostly used for tracing + CC callbacks)
				Ptr<RdmaQueuePair> lastQp = m_rdmaEQ->GetQp(qIndex);
                // Dequeue the next RDMA packet for that QP (e.g., based on snd_nxt, unscheduled tags, etc.)
				p = m_rdmaEQ->DequeueQindex(qIndex);



				// transmit
				m_traceQpDequeue(p, lastQp);
				TransmitStart(p);

				// update for the next avail time
				m_rdmaPktSent(lastQp, p, m_tInterframeGap);
			}else { // no packet to send
                // No eligible traffic right now (often: PFC paused or all QPs not yet available).
                // If QCN/CC is enabled, the NIC may want to wake up exactly when the earliest
                // QP becomes available (min m_nextAvail among active QPs).
                //
                // This avoids spinning / calling DequeueAndTransmit repeatedly when pacing
                // says “wait until time T”.
				NS_LOG_INFO("PAUSE prohibits send at node " << m_node->GetId());
				Time t = Simulator::GetMaximumSimulationTime();
				for (uint32_t i = 0; i < m_rdmaEQ->GetFlowCount(); i++){
					Ptr<RdmaQueuePair> qp = m_rdmaEQ->GetQp(i);
					if (qp->GetBytesLeft() == 0)
						continue;
					t = Min(qp->m_nextAvail, t);
				}
                // Schedule a single “wake-up” event (if none already pending) for that time.
				if (m_nextSend.IsExpired() && t < Simulator::GetMaximumSimulationTime() && t > Simulator::Now()){
					m_nextSend = Simulator::Schedule(t - Simulator::Now(), &QbbNetDevice::DequeueAndTransmit, this);
				}
			}
			return;
		}else{   //switch, doesn't care about qcn, just send
                 // ==========================
                 // Switch-side port scheduling
                 // ==========================
                 //
                 // Switch does NOT consult RdmaEgressQueue; it simply dequeues from the
                 // output queues in round-robin order, subject to PFC pause (m_paused[]).

            p = m_queue->DequeueRR(m_paused);		//this is round-robin
			if (p){
				m_snifferTrace(p);
				m_promiscSnifferTrace(p);
				Ipv4Header h;
				Ptr<Packet> packet = p->Copy();
				uint16_t protocol = 0;
				ProcessHeader(packet, protocol);
				packet->RemoveHeader(h);
				FlowIdTag t;
				uint32_t qIndex = m_queue->GetLastQueue();
				if (qIndex == 0){//this is a pause or cnp, send it immediately!
					m_node->SwitchNotifyDequeue(m_ifIndex, qIndex, p);
					p->RemovePacketTag(t);
				}else{
					m_node->SwitchNotifyDequeue(m_ifIndex, qIndex, p);
					p->RemovePacketTag(t);
				}
				m_traceDequeue(p, qIndex);
				TransmitStart(p);
				return;
			}else{ //No queue can deliver any packet
				NS_LOG_INFO("PAUSE prohibits send at node " << m_node->GetId());
				if (m_node->GetNodeType() == 0 && m_qcnEnabled){ //nothing to send, possibly due to qcn flow control, if so reschedule sending
					Time t = Simulator::GetMaximumSimulationTime();
					for (uint32_t i = 0; i < m_rdmaEQ->GetFlowCount(); i++){
						Ptr<RdmaQueuePair> qp = m_rdmaEQ->GetQp(i);
						if (qp->GetBytesLeft() == 0)
							continue;
						t = Min(qp->m_nextAvail, t);
					}
					if (m_nextSend.IsExpired() && t < Simulator::GetMaximumSimulationTime() && t > Simulator::Now()){
						m_nextSend = Simulator::Schedule(t - Simulator::Now(), &QbbNetDevice::DequeueAndTransmit, this);
					}
				}
			}
		}
		return;
	}

	void
		QbbNetDevice::Resume(unsigned qIndex)
	{
		NS_LOG_FUNCTION(this << qIndex);
		NS_ASSERT_MSG(m_paused[qIndex], "Must be PAUSEd");
		m_paused[qIndex] = false;
		NS_LOG_INFO("Node " << m_node->GetId() << " dev " << m_ifIndex << " queue " << qIndex <<
			" resumed at " << Simulator::Now().GetSeconds());
		DequeueAndTransmit();
	}

	void
		QbbNetDevice::Receive(Ptr<Packet> packet)
	{
		NS_LOG_FUNCTION(this << packet);
		if (!m_linkUp){
			m_traceDrop(packet, 0);
			return;
		}

		if (m_receiveErrorModel && m_receiveErrorModel->IsCorrupt(packet))
		{
			// 
			// If we have an error model and it indicates that it is time to lose a
			// corrupted packet, don't forward this packet up, let it go.
			//
			m_phyRxDropTrace(packet);
			return;
		}

		m_macRxTrace(packet);
		CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
		ch.getInt = 1; // parse INT header
		packet->PeekHeader(ch);

//        NS_LOG_UNCOND(
//            "Haoyu ---1 Receive Packet at node " << m_node->GetId() <<
//            " NodeType " << m_node->GetNodeType() <<
//            " ch L3Prot " << std::hex << (unsigned)ch.l3Prot <<
//            " ch SIP " << Ipv4Address(ch.sip) <<
//            " ch DIP " << Ipv4Address(ch.dip) <<
//            " ch SPort " << ch.udp.sport <<
//            " ch DPort " << ch.udp.dport <<
//            " ch Seq " << ch.udp.seq <<
//            " ch PG " << (unsigned)ch.udp.pg
//
//                      << " with INT header " << ch.getInt
//                      );

		if (ch.l3Prot == 0xFE){ // PFC
			if (!m_qbbEnabled) return;
			unsigned qIndex = ch.pfc.qIndex;
			if (ch.pfc.time > 0){
				m_tracePfc(1, qIndex);
				m_paused[qIndex] = true;
			}else{
				m_tracePfc(0, qIndex);
				Resume(qIndex);
			}
		}else { // non-PFC packets (data, ACK, NACK, CNP...)
			if (m_node->GetNodeType() > 0){ // switch
				packet->AddPacketTag(FlowIdTag(m_ifIndex));
				m_node->SwitchReceiveFromDevice(this, packet, ch);
			}else { // NIC
				// send to RdmaHw
				int ret = m_rdmaReceiveCb(packet, ch);
				// TODO we may based on the ret do something
			}
		}
		return;
	}

	bool QbbNetDevice::Send(Ptr<Packet> packet, const Address &dest, uint16_t protocolNumber)
	{
		NS_ASSERT_MSG(false, "QbbNetDevice::Send not implemented yet\n");
		return false;
	}

	bool QbbNetDevice::SwitchSend (uint32_t qIndex, Ptr<Packet> packet, CustomHeader &ch){
		m_macTxTrace(packet);
		m_traceEnqueue(packet, qIndex);
		m_queue->Enqueue(packet, qIndex);
		DequeueAndTransmit();
		return true;
	}

	void QbbNetDevice::SendPfc(uint32_t qIndex, uint32_t type){
		Ptr<Packet> p = Create<Packet>(0);
		PauseHeader pauseh((type == 0 ? m_pausetime : 0), m_queue->GetNBytes(qIndex), qIndex);
		p->AddHeader(pauseh);
		Ipv4Header ipv4h;  // Prepare IPv4 header
		ipv4h.SetProtocol(0xFE);
		ipv4h.SetSource(m_node->GetObject<Ipv4>()->GetAddress(m_ifIndex, 0).GetLocal());
		ipv4h.SetDestination(Ipv4Address("255.255.255.255"));
		ipv4h.SetPayloadSize(p->GetSize());
		ipv4h.SetTtl(1);
		ipv4h.SetIdentification(UniformRandomVariable::GetGlobalRng()->GetInteger(0, 65535));
		p->AddHeader(ipv4h);
		AddHeader(p, 0x800);
		CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
		p->PeekHeader(ch);
		SwitchSend(0, p, ch);
	}

	bool
		QbbNetDevice::Attach(Ptr<QbbChannel> ch)
	{
		NS_LOG_FUNCTION(this << &ch);
		m_channel = ch;
		m_channel->Attach(this);
		NotifyLinkUp();
		return true;
	}

	bool
		QbbNetDevice::TransmitStart(Ptr<Packet> p)
	{
		NS_LOG_FUNCTION(this << p);
		NS_LOG_LOGIC("UID is " << p->GetUid() << ")");

        CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
        ch.getInt = 1; // parse INT header
        p->PeekHeader(ch);
//        NS_LOG_UNCOND(
//            "Haoyu ---3 Transmit Packet at node " << m_node->GetId() <<
//            ", size: " << p->GetSize() <<
//            ", sip: " << ch.sip <<
//            ", dip: " << ch.dip <<
//            ", sport: " << ch.udp.sport <<
//            ", dport: " << ch.udp.dport <<
//            ", pg: " << ch.udp.pg
//        );


		//
		// This function is called to start the process of transmitting a packet.
		// We need to tell the channel that we've started wiggling the wire and
		// schedule an event that will be executed when the transmission is complete.
		//
		NS_ASSERT_MSG(m_txMachineState == READY, "Must be READY to transmit");
		m_txMachineState = BUSY;
		m_currentPkt = p;
		m_phyTxBeginTrace(m_currentPkt);
		Time txTime = m_bps.CalculateBytesTxTime(p->GetSize());
		Time txCompleteTime = txTime + m_tInterframeGap;
		NS_LOG_LOGIC("Schedule TransmitCompleteEvent in " << txCompleteTime.GetSeconds() << "sec");
		Simulator::Schedule(txCompleteTime, &QbbNetDevice::TransmitComplete, this);

		bool result = m_channel->TransmitStart(p, this, txTime);
		if (result == false)
		{
			m_phyTxDropTrace(p);
		}
		return result;
	}

	Ptr<Channel>
		QbbNetDevice::GetChannel(void) const
	{
		return m_channel;
	}

   bool QbbNetDevice::IsQbb(void) const{
	   return true;
   }

   void QbbNetDevice::NewQp(Ptr<RdmaQueuePair> qp){
	   qp->m_nextAvail = Simulator::Now();
	   DequeueAndTransmit();
   }
   void QbbNetDevice::ReassignedQp(Ptr<RdmaQueuePair> qp){
	   DequeueAndTransmit();
   }
   void QbbNetDevice::TriggerTransmit(void){
	   DequeueAndTransmit();
   }

	void QbbNetDevice::SetQueue(Ptr<BEgressQueue> q){
		NS_LOG_FUNCTION(this << q);
		m_queue = q;
	}

	Ptr<BEgressQueue> QbbNetDevice::GetQueue(){
		return m_queue;
	}

	Ptr<RdmaEgressQueue> QbbNetDevice::GetRdmaQueue(){
		return m_rdmaEQ;
	}

	void QbbNetDevice::RdmaEnqueueHighPrioQ(Ptr<Packet> p){
		m_traceEnqueue(p, 0);
		m_rdmaEQ->EnqueueHighPrioQ(p);
	}

	void QbbNetDevice::TakeDown(){
		// TODO: delete packets in the queue, set link down
		if (m_node->GetNodeType() == 0){
			// clean the high prio queue
			m_rdmaEQ->CleanHighPrio(m_traceDrop);
			// notify driver/RdmaHw that this link is down
			m_rdmaLinkDownCb(this);
		}else { // switch
			// clean the queue
			for (uint32_t i = 0; i < qCnt; i++)
				m_paused[i] = false;
			while (1){
				Ptr<Packet> p = m_queue->DequeueRR(m_paused);
				if (!p)
					 break;
				m_traceDrop(p, m_queue->GetLastQueue());
			}
			// TODO: Notify switch that this link is down
		}
		m_linkUp = false;
	}

	void QbbNetDevice::UpdateNextAvail(Time t){
		if (!m_nextSend.IsExpired() && t <  Time(m_nextSend.GetTs())){
			Simulator::Cancel(m_nextSend);
			Time delta = t < Simulator::Now() ? Time(0) : t - Simulator::Now();
			m_nextSend = Simulator::Schedule(delta, &QbbNetDevice::DequeueAndTransmit, this);
		}
	}
} // namespace ns3
