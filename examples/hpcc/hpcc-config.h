#ifndef HPCC_CONFIG_H
#define HPCC_CONFIG_H

#include <string>
#include <unordered_map>
#include <iostream>
#include <yaml-cpp/yaml.h>
#include <fmt/format.h>

/**
 * @brief Holds link-down event information.
 */
struct LinkDownInfo {
    uint64_t time = 0;
    uint32_t from_node = 0;
    uint32_t to_node = 0;
};

/**
 * @class HpccConfig
 * @brief Reads and holds configuration parameters for an HPCC simulation
 *        from a YAML file.
 *
 * All field types are chosen to match the types used in the simulation code
 * (hpcc-haoyu.cc) so that the config object can be used as a drop-in
 * replacement for the scattered global variables.
 */
class HpccConfig {
  public:
    /**
     * @brief Constructs an HpccConfig object by parsing a YAML file.
     * @param filename The path to the YAML configuration file.
     * @throws std::runtime_error if the file cannot be opened or parsed.
     */
    explicit HpccConfig(const std::string& filename);

    /**
     * @brief Prints all configuration values to stdout (mirrors the
     *        cout output from the original config.txt parser).
     */
    void print() const;

    // -----------------------------------------------------------------------
    // Public Getters — read-only access to parsed parameters
    // -----------------------------------------------------------------------

    // Congestion control
    uint32_t get_cc_mode() const { return cc_mode; }
    bool get_enable_qcn() const { return enable_qcn; }
    bool get_use_dynamic_pfc_threshold() const { return use_dynamic_pfc_threshold; }
    bool get_clamp_target_rate() const { return clamp_target_rate; }

    // Packet / L2
    uint32_t get_pause_time() const { return pause_time; }
    uint32_t get_packet_payload_size() const { return packet_payload_size; }
    uint32_t get_l2_chunk_size() const { return l2_chunk_size; }
    uint32_t get_l2_ack_interval() const { return l2_ack_interval; }
    bool get_l2_back_to_zero() const { return l2_back_to_zero; }

    // Files
    const std::string& get_topology_file() const { return topology_file; }
    const std::string& get_flow_file() const { return flow_file; }
    const std::string& get_trace_file() const { return trace_file; }
    const std::string& get_trace_output_file() const { return trace_output_file; }
    const std::string& get_fct_output_file() const { return fct_output_file; }
    const std::string& get_pfc_output_file() const { return pfc_output_file; }
    const std::string& get_bottleneck_output_file() const { return bottleneck_output_file; }

    // Simulation
    double get_simulator_stop_time() const { return simulator_stop_time; }

    // Rate control
    double get_alpha_resume_interval() const { return alpha_resume_interval; }
    double get_rate_decrease_interval() const { return rate_decrease_interval; }
    double get_rp_timer() const { return rp_timer; }
    double get_ewma_gain() const { return ewma_gain; }
    uint32_t get_fast_recovery_times() const { return fast_recovery_times; }
    const std::string& get_rate_ai() const { return rate_ai; }
    const std::string& get_rate_hai() const { return rate_hai; }
    const std::string& get_min_rate() const { return min_rate; }
    const std::string& get_dctcp_rate_ai() const { return dctcp_rate_ai; }

    // Error
    double get_error_rate_per_link() const { return error_rate_per_link; }

    // Window / INT
    uint32_t get_has_win() const { return has_win; }
    uint32_t get_global_t() const { return global_t; }
    bool get_var_win() const { return var_win; }
    bool get_fast_react() const { return fast_react; }
    double get_u_target() const { return u_target; }
    uint32_t get_mi_thresh() const { return mi_thresh; }
    uint32_t get_int_multi() const { return int_multi; }
    bool get_multi_rate() const { return multi_rate; }
    bool get_sample_feedback() const { return sample_feedback; }
    uint32_t get_mb_mode() const { return mb_mode; }
    double get_mb_gamma() const { return mb_gamma; }
    double get_fs_alpha() const { return fs_alpha; }
    double get_fs_beta() const { return fs_beta; }
    double get_fs_init_frac() const { return fs_init_frac; }
    uint32_t get_ecmp_seed_offset() const { return ecmp_seed_offset; }
    uint32_t get_mix_fs_dport() const { return mix_fs_dport; }
    bool get_fs_rcp_window() const { return fs_rcp_window; }
    std::string get_fs_min_rate() const { return fs_min_rate; }
    const std::map<uint32_t,double>& get_dwrr_weights() const { return dwrr_weights; }
    double get_fs_d_scale() const { return fs_d_scale; }
    bool get_fs_disable_window() const { return fs_disable_window; }
    double get_pint_log_base() const { return pint_log_base; }
    double get_pint_prob() const { return pint_prob; }
    bool get_rate_bound() const { return rate_bound; }

    // ACK
    uint32_t get_ack_high_prio() const { return ack_high_prio; }

    // Link down
    const LinkDownInfo& get_link_down() const { return link_down; }

    // Trace
    uint32_t get_enable_trace() const { return enable_trace; }

    // ECN maps
    const std::unordered_map<uint64_t, uint32_t>& get_kmax_map() const { return kmax_map; }
    const std::unordered_map<uint64_t, uint32_t>& get_kmin_map() const { return kmin_map; }
    const std::unordered_map<uint64_t, double>& get_pmax_map() const { return pmax_map; }

    // Buffer / queue monitoring
    uint32_t get_buffer_size() const { return buffer_size; }
    const std::string& get_qlen_mon_file() const { return qlen_mon_file; }
    uint32_t get_qlen_dump_interval() const { return qlen_dump_interval; }
    uint32_t get_qlen_mon_interval() const { return qlen_mon_interval; }
    uint64_t get_qlen_mon_start() const { return qlen_mon_start; }
    uint64_t get_qlen_mon_end() const { return qlen_mon_end; }

  private:
    // -----------------------------------------------------------------------
    // Private helper
    // -----------------------------------------------------------------------
    void loadFromYaml(const std::string& filename);

    // -----------------------------------------------------------------------
    // Member variables — defaults match hpcc-haoyu.cc globals
    // -----------------------------------------------------------------------

    // Congestion control
    uint32_t cc_mode = 1;
    bool enable_qcn = true;
    bool use_dynamic_pfc_threshold = true;
    bool clamp_target_rate = false;

    // Packet / L2
    uint32_t pause_time = 5;
    uint32_t packet_payload_size = 1000;
    uint32_t l2_chunk_size = 0;
    uint32_t l2_ack_interval = 0;
    bool l2_back_to_zero = false;

    // Files
    std::string topology_file;
    std::string flow_file;
    std::string trace_file;
    std::string trace_output_file;
    std::string fct_output_file = "fct.txt";
    std::string pfc_output_file = "pfc.txt";
    std::string bottleneck_output_file = "bottleneck.txt";

    // Simulation
    double simulator_stop_time = 3.01;

    // Rate control
    double alpha_resume_interval = 55.0;
    double rate_decrease_interval = 4.0;
    double rp_timer = 0.0;
    double ewma_gain = 1.0 / 16.0;
    uint32_t fast_recovery_times = 5;
    std::string rate_ai;
    std::string rate_hai;
    std::string min_rate = "100Mb/s";
    std::string dctcp_rate_ai = "1000Mb/s";

    // Error
    double error_rate_per_link = 0.0;

    // Window / INT
    uint32_t has_win = 1;
    uint32_t global_t = 1;
    bool var_win = false;
    bool fast_react = true;
    double u_target = 0.95;
    uint32_t mi_thresh = 5;
    uint32_t int_multi = 1;
    bool multi_rate = true;
    bool sample_feedback = false;
    // HPCC-MB (multi-bottleneck fairness, sender-only). mb_mode 0 = stock HPCC.
    uint32_t mb_mode = 0;    // 0=off, 1=k-aware AI
    double mb_gamma = 1.0;   // correction strength
    // HPCC-FS (cc_mode 11) RCP knobs; defaults reproduce the paper's headline runs.
    double fs_alpha = 0.4;
    double fs_beta = 0.226;
    double fs_init_frac = 0.5;        // initial fair rate = fs_init_frac * C
    uint32_t ecmp_seed_offset = 0;    // added to each switch id as its ECMP hash seed (0 = stock behavior)
    uint32_t mix_fs_dport = 0;        // cc_mode 12: flows with dport >= this are the HPCC-FS class (0 = off)
    bool fs_rcp_window = false;       // cc_mode 11: window = R*baseRTT (canonical RCP endpoint)
    std::string fs_min_rate = "100Mb/s"; // cc_mode 11: floor on the adopted fair rate (separate from cold-start min_rate)
    std::map<uint32_t,double> dwrr_weights; // per-queue DWRR weights at switch egress (empty = stock RR)
    double fs_d_scale = 1.0;          // cc_mode 11: scale RCP control interval d
    bool fs_disable_window = true;    // FS mode is rate-only (no per-flow window cap)
    double pint_log_base = 1.05;
    double pint_prob = 1.0;
    bool rate_bound = true;

    // ACK
    uint32_t ack_high_prio = 0;

    // Link down
    LinkDownInfo link_down;

    // Trace
    uint32_t enable_trace = 1;

    // ECN maps
    std::unordered_map<uint64_t, uint32_t> kmax_map;
    std::unordered_map<uint64_t, uint32_t> kmin_map;
    std::unordered_map<uint64_t, double> pmax_map;

    // Buffer / queue monitoring
    uint32_t buffer_size = 16;
    std::string qlen_mon_file;
    uint32_t qlen_dump_interval = 100000000;
    uint32_t qlen_mon_interval = 100;
    uint64_t qlen_mon_start = 2000000000;
    uint64_t qlen_mon_end = 2100000000;
};

#endif // HPCC_CONFIG_H
