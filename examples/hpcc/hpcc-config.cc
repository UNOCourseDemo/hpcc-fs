#include "hpcc-config.h"
#include <stdexcept>

HpccConfig::HpccConfig(const std::string& filename) {
    loadFromYaml(filename);
}

void HpccConfig::loadFromYaml(const std::string& filename) {
    YAML::Node config;
    try {
        config = YAML::LoadFile(filename);
    } catch (const YAML::Exception& e) {
        throw std::runtime_error("Error: Could not open/parse YAML config file: "
                                 + filename + "\n" + e.what());
    }

    // --- Congestion Control ---
    if (config["cc_mode"])                    cc_mode = config["cc_mode"].as<uint32_t>();
    if (config["enable_qcn"])                 enable_qcn = config["enable_qcn"].as<bool>();
    if (config["use_dynamic_pfc_threshold"])  use_dynamic_pfc_threshold = config["use_dynamic_pfc_threshold"].as<bool>();
    if (config["clamp_target_rate"])          clamp_target_rate = config["clamp_target_rate"].as<bool>();

    // --- Packet / L2 ---
    if (config["pause_time"])            pause_time = config["pause_time"].as<uint32_t>();
    if (config["packet_payload_size"])   packet_payload_size = config["packet_payload_size"].as<uint32_t>();
    if (config["l2_chunk_size"])         l2_chunk_size = config["l2_chunk_size"].as<uint32_t>();
    if (config["l2_ack_interval"])       l2_ack_interval = config["l2_ack_interval"].as<uint32_t>();
    if (config["l2_back_to_zero"])       l2_back_to_zero = config["l2_back_to_zero"].as<bool>();

    // --- Files ---
    if (config["topology_file"])      topology_file = config["topology_file"].as<std::string>();
    if (config["flow_file"])          flow_file = config["flow_file"].as<std::string>();
    if (config["trace_file"])         trace_file = config["trace_file"].as<std::string>();
    if (config["trace_output_file"])  trace_output_file = config["trace_output_file"].as<std::string>();
    if (config["fct_output_file"])    fct_output_file = config["fct_output_file"].as<std::string>();
    if (config["pfc_output_file"])    pfc_output_file = config["pfc_output_file"].as<std::string>();
    if (config["bottleneck_output_file"]) bottleneck_output_file = config["bottleneck_output_file"].as<std::string>();

    // --- Simulation ---
    if (config["simulator_stop_time"]) simulator_stop_time = config["simulator_stop_time"].as<double>();

    // --- Rate Control ---
    if (config["alpha_resume_interval"])  alpha_resume_interval = config["alpha_resume_interval"].as<double>();
    if (config["rate_decrease_interval"]) rate_decrease_interval = config["rate_decrease_interval"].as<double>();
    if (config["rp_timer"])              rp_timer = config["rp_timer"].as<double>();
    if (config["ewma_gain"])             ewma_gain = config["ewma_gain"].as<double>();
    if (config["fast_recovery_times"])   fast_recovery_times = config["fast_recovery_times"].as<uint32_t>();
    if (config["rate_ai"])               rate_ai = config["rate_ai"].as<std::string>();
    if (config["rate_hai"])              rate_hai = config["rate_hai"].as<std::string>();
    if (config["min_rate"])              min_rate = config["min_rate"].as<std::string>();
    if (config["dctcp_rate_ai"])         dctcp_rate_ai = config["dctcp_rate_ai"].as<std::string>();

    // --- Error ---
    if (config["error_rate_per_link"]) error_rate_per_link = config["error_rate_per_link"].as<double>();

    // --- Window / INT ---
    if (config["has_win"])          has_win = config["has_win"].as<uint32_t>();
    if (config["global_t"])         global_t = config["global_t"].as<uint32_t>();
    if (config["var_win"])          var_win = config["var_win"].as<bool>();
    if (config["fast_react"])       fast_react = config["fast_react"].as<bool>();
    if (config["u_target"])         u_target = config["u_target"].as<double>();
    if (config["mi_thresh"])        mi_thresh = config["mi_thresh"].as<uint32_t>();
    if (config["int_multi"])        int_multi = config["int_multi"].as<uint32_t>();
    if (config["multi_rate"])       multi_rate = config["multi_rate"].as<bool>();
    if (config["sample_feedback"])  sample_feedback = config["sample_feedback"].as<bool>();
    if (config["mb_mode"])          mb_mode = config["mb_mode"].as<uint32_t>();
    if (config["mb_gamma"])         mb_gamma = config["mb_gamma"].as<double>();
    if (config["fs_alpha"])         fs_alpha = config["fs_alpha"].as<double>();
    if (config["fs_beta"])          fs_beta = config["fs_beta"].as<double>();
    if (config["fs_init_frac"])     fs_init_frac = config["fs_init_frac"].as<double>();
    if (config["ecmp_seed_offset"]) ecmp_seed_offset = config["ecmp_seed_offset"].as<uint32_t>();
    if (config["mix_fs_dport"])     mix_fs_dport = config["mix_fs_dport"].as<uint32_t>();
    if (config["fs_rcp_window"])    fs_rcp_window = config["fs_rcp_window"].as<bool>();
    if (config["fs_d_scale"])       fs_d_scale = config["fs_d_scale"].as<double>();
    if (config["dwrr_weights"])
        for (auto it : config["dwrr_weights"])
            dwrr_weights[it.first.as<uint32_t>()] = it.second.as<double>();
    if (config["fs_disable_window"]) fs_disable_window = config["fs_disable_window"].as<bool>();
    if (config["pint_log_base"])    pint_log_base = config["pint_log_base"].as<double>();
    if (config["pint_prob"])        pint_prob = config["pint_prob"].as<double>();
    if (config["rate_bound"])       rate_bound = config["rate_bound"].as<bool>();

    // --- ACK ---
    if (config["ack_high_prio"]) ack_high_prio = config["ack_high_prio"].as<uint32_t>();

    // --- Link Down ---
    if (config["link_down"]) {
        auto ld = config["link_down"];
        if (ld["time"])      link_down.time = ld["time"].as<uint64_t>();
        if (ld["from_node"]) link_down.from_node = ld["from_node"].as<uint32_t>();
        if (ld["to_node"])   link_down.to_node = ld["to_node"].as<uint32_t>();
    }

    // --- Trace ---
    if (config["enable_trace"]) enable_trace = config["enable_trace"].as<uint32_t>();

    // --- ECN Maps ---
    if (config["kmax_map"]) {
        kmax_map.clear();
        for (auto it = config["kmax_map"].begin(); it != config["kmax_map"].end(); ++it) {
            uint64_t rate = it->first.as<uint64_t>();
            uint32_t k = it->second.as<uint32_t>();
            kmax_map[rate] = k;
        }
    }
    if (config["kmin_map"]) {
        kmin_map.clear();
        for (auto it = config["kmin_map"].begin(); it != config["kmin_map"].end(); ++it) {
            uint64_t rate = it->first.as<uint64_t>();
            uint32_t k = it->second.as<uint32_t>();
            kmin_map[rate] = k;
        }
    }
    if (config["pmax_map"]) {
        pmax_map.clear();
        for (auto it = config["pmax_map"].begin(); it != config["pmax_map"].end(); ++it) {
            uint64_t rate = it->first.as<uint64_t>();
            double p = it->second.as<double>();
            pmax_map[rate] = p;
        }
    }

    // --- Buffer / Queue Monitoring ---
    if (config["buffer_size"])    buffer_size = config["buffer_size"].as<uint32_t>();
    if (config["qlen_mon_file"]) qlen_mon_file = config["qlen_mon_file"].as<std::string>();
    if (config["qlen_dump_interval"]) qlen_dump_interval = config["qlen_dump_interval"].as<uint32_t>();
    if (config["qlen_mon_interval"]) qlen_mon_interval = config["qlen_mon_interval"].as<uint32_t>();
    if (config["qlen_mon_start"]) qlen_mon_start = config["qlen_mon_start"].as<uint64_t>();
    if (config["qlen_mon_end"])   qlen_mon_end = config["qlen_mon_end"].as<uint64_t>();
}

void HpccConfig::print() const {
    // Consistent 30-char column for key names using fmt
    fmt::print("{:-^60}\n", " HPCC Configuration ");

    fmt::print("\n{:=^60}\n", " Congestion Control ");
    fmt::print("{:<30} {}\n", "CC_MODE", cc_mode);
    fmt::print("{:<30} {}\n", "ENABLE_QCN", enable_qcn ? "Yes" : "No");
    fmt::print("{:<30} {}\n", "USE_DYNAMIC_PFC_THRESHOLD", use_dynamic_pfc_threshold ? "Yes" : "No");
    fmt::print("{:<30} {}\n", "CLAMP_TARGET_RATE", clamp_target_rate ? "Yes" : "No");

    fmt::print("\n{:=^60}\n", " Packet / L2 ");
    fmt::print("{:<30} {}\n", "PAUSE_TIME", pause_time);
    fmt::print("{:<30} {}\n", "PACKET_PAYLOAD_SIZE", packet_payload_size);
    fmt::print("{:<30} {}\n", "L2_CHUNK_SIZE", l2_chunk_size);
    fmt::print("{:<30} {}\n", "L2_ACK_INTERVAL", l2_ack_interval);
    fmt::print("{:<30} {}\n", "L2_BACK_TO_ZERO", l2_back_to_zero ? "Yes" : "No");

    fmt::print("\n{:=^60}\n", " Files ");
    fmt::print("{:<30} {}\n", "TOPOLOGY_FILE", topology_file);
    fmt::print("{:<30} {}\n", "FLOW_FILE", flow_file);
    fmt::print("{:<30} {}\n", "TRACE_FILE", trace_file);
    fmt::print("{:<30} {}\n", "TRACE_OUTPUT_FILE", trace_output_file);
    fmt::print("{:<30} {}\n", "FCT_OUTPUT_FILE", fct_output_file);
    fmt::print("{:<30} {}\n", "PFC_OUTPUT_FILE", pfc_output_file);
    fmt::print("{:<30} {}\n", "BOTTLENECK_OUTPUT_FILE", bottleneck_output_file);

    fmt::print("\n{:=^60}\n", " Simulation ");
    fmt::print("{:<30} {}\n", "SIMULATOR_STOP_TIME", simulator_stop_time);

    fmt::print("\n{:=^60}\n", " Rate Control ");
    fmt::print("{:<30} {}\n", "ALPHA_RESUME_INTERVAL", alpha_resume_interval);
    fmt::print("{:<30} {}\n", "RATE_DECREASE_INTERVAL", rate_decrease_interval);
    fmt::print("{:<30} {}\n", "RP_TIMER", rp_timer);
    fmt::print("{:<30} {}\n", "EWMA_GAIN", ewma_gain);
    fmt::print("{:<30} {}\n", "FAST_RECOVERY_TIMES", fast_recovery_times);
    fmt::print("{:<30} {}\n", "RATE_AI", rate_ai);
    fmt::print("{:<30} {}\n", "RATE_HAI", rate_hai);
    fmt::print("{:<30} {}\n", "MIN_RATE", min_rate);
    fmt::print("{:<30} {}\n", "DCTCP_RATE_AI", dctcp_rate_ai);

    fmt::print("\n{:=^60}\n", " Error ");
    fmt::print("{:<30} {}\n", "ERROR_RATE_PER_LINK", error_rate_per_link);

    fmt::print("\n{:=^60}\n", " Window / INT ");
    fmt::print("{:<30} {}\n", "HAS_WIN", has_win);
    fmt::print("{:<30} {}\n", "GLOBAL_T", global_t);
    fmt::print("{:<30} {}\n", "VAR_WIN", var_win);
    fmt::print("{:<30} {}\n", "FAST_REACT", fast_react);
    fmt::print("{:<30} {}\n", "U_TARGET", u_target);
    fmt::print("{:<30} {}\n", "MI_THRESH", mi_thresh);
    fmt::print("{:<30} {}\n", "INT_MULTI", int_multi);
    fmt::print("{:<30} {}\n", "MULTI_RATE", multi_rate);
    fmt::print("{:<30} {}\n", "SAMPLE_FEEDBACK", sample_feedback);
    fmt::print("{:<30} {}\n", "MB_MODE", mb_mode);
    fmt::print("{:<30} {}\n", "MB_GAMMA", mb_gamma);
    fmt::print("{:<30} {}\n", "FS_ALPHA", fs_alpha);
    fmt::print("{:<30} {}\n", "FS_BETA", fs_beta);
    fmt::print("{:<30} {}\n", "FS_INIT_FRAC", fs_init_frac);
    fmt::print("{:<30} {}\n", "FS_DISABLE_WINDOW", fs_disable_window);
    fmt::print("{:<30} {}\n", "PINT_LOG_BASE", pint_log_base);
    fmt::print("{:<30} {}\n", "PINT_PROB", pint_prob);
    fmt::print("{:<30} {}\n", "RATE_BOUND", rate_bound);

    fmt::print("\n{:=^60}\n", " ACK / Link Down / Trace ");
    fmt::print("{:<30} {}\n", "ACK_HIGH_PRIO", ack_high_prio);
    fmt::print("{:<30} {} {} {}\n", "LINK_DOWN", link_down.time, link_down.from_node, link_down.to_node);
    fmt::print("{:<30} {}\n", "ENABLE_TRACE", enable_trace);

    fmt::print("\n{:=^60}\n", " ECN Maps ");
    fmt::print("{:<30}", "KMAX_MAP");
    for (auto& [rate, k] : kmax_map) fmt::print(" {}:{}", rate, k);
    fmt::print("\n");

    fmt::print("{:<30}", "KMIN_MAP");
    for (auto& [rate, k] : kmin_map) fmt::print(" {}:{}", rate, k);
    fmt::print("\n");

    fmt::print("{:<30}", "PMAX_MAP");
    for (auto& [rate, p] : pmax_map) fmt::print(" {}:{}", rate, p);
    fmt::print("\n");

    fmt::print("\n{:=^60}\n", " Buffer / Queue Monitoring ");
    fmt::print("{:<30} {}\n", "BUFFER_SIZE", buffer_size);
    fmt::print("{:<30} {}\n", "QLEN_MON_FILE", qlen_mon_file);
    fmt::print("{:<30} {}\n", "QLEN_DUMP_INTERVAL", qlen_dump_interval);
    fmt::print("{:<30} {}\n", "QLEN_MON_INTERVAL", qlen_mon_interval);
    fmt::print("{:<30} {}\n", "QLEN_MON_START", qlen_mon_start);
    fmt::print("{:<30} {}\n", "QLEN_MON_END", qlen_mon_end);

    fmt::print("{:-^60}\n", "");
}
