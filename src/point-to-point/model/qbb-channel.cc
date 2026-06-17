/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007, 2008 University of Washington
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
 */

#include "qbb-channel.h"

#include "qbb-net-device.h"

#include "ns3/log.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/trace-source-accessor.h"

#include <fstream>
#include <iostream>

NS_LOG_COMPONENT_DEFINE("QbbChannel");

namespace ns3
{

NS_OBJECT_ENSURE_REGISTERED(QbbChannel);

TypeId
QbbChannel::GetTypeId()
{
    static TypeId tid = TypeId("ns3::QbbChannel")
                            .SetParent<Channel>()
                            .AddConstructor<QbbChannel>()
                            .AddAttribute("Delay",
                                          "Transmission delay through the channel",
                                          TimeValue(Seconds(0)),
                                          MakeTimeAccessor(&QbbChannel::m_delay),
                                          MakeTimeChecker())
                            .AddTraceSource("TxRxQbb",
                                            "Trace source indicating transmission of packet from "
                                            "the QbbChannel, used by the Animation interface.",
                                            MakeTraceSourceAccessor(&QbbChannel::m_txrxQbb),
                                            "ns3::PointToPointChannel::TxRxAnimationCallback");
    return tid;
}

//
// By default, you get a channel that
// has an "infitely" fast transmission speed and zero delay.
QbbChannel::QbbChannel()
    : PointToPointChannel()
{
    NS_LOG_FUNCTION_NOARGS();
    m_nDevices = 0;
}

void
QbbChannel::Attach(Ptr<QbbNetDevice> device)
{
    NS_LOG_FUNCTION(this << device);
    NS_ASSERT_MSG(m_nDevices < N_DEVICES, "Only two devices permitted");
    NS_ASSERT(device);

    m_link[m_nDevices++].m_src = device;
    //
    // If we have both devices connected to the channel, then finish introducing
    // the two halves and set the links to IDLE.
    //
    if (m_nDevices == N_DEVICES)
    {
        m_link[0].m_dst = m_link[1].m_src;
        m_link[1].m_dst = m_link[0].m_src;
        m_link[0].m_state = IDLE;
        m_link[1].m_state = IDLE;
    }
}

bool
QbbChannel::TransmitStart(Ptr<Packet> p, Ptr<PointToPointNetDevice> src, Time txTime)
{
    NS_LOG_FUNCTION(this << p << src);
    NS_LOG_LOGIC("UID is " << p->GetUid() << ")");

    NS_ASSERT(m_link[0].m_state != INITIALIZING);
    NS_ASSERT(m_link[1].m_state != INITIALIZING);

    uint32_t wire = src == m_link[0].m_src ? 0 : 1;

    CustomHeader ch(CustomHeader::L2_Header | CustomHeader::L3_Header | CustomHeader::L4_Header);
    ch.getInt = 1; // parse INT header
    p->PeekHeader(ch);
//    NS_LOG_UNCOND(
//        "Haoyu ---2 Transmit Packet at node " << src->GetNode()->GetId() <<
//        ", to node " << m_link[wire].m_dst->GetNode()->GetId() <<
//        ", size: " << p->GetSize() <<
//        ", sip: " << ch.sip <<
//        ", dip: " << ch.dip <<
//        ", sport: " << ch.udp.sport <<
//        ", dport: " << ch.udp.dport <<
//        ", pg: " << ch.udp.pg
//    );


    Simulator::ScheduleWithContext(m_link[wire].m_dst->GetNode()->GetId(),
                                   txTime + m_delay,
                                   &QbbNetDevice::Receive,
                                   m_link[wire].m_dst,
                                   p);

    // Call the tx anim callback on the net device
    m_txrxQbb(p, src, m_link[wire].m_dst, txTime, txTime + m_delay);
    return true;
}

std::size_t
QbbChannel::GetNDevices() const
{
    NS_LOG_FUNCTION_NOARGS();
    return m_nDevices;
}

Ptr<QbbNetDevice>
QbbChannel::GetQbbDevice(uint32_t i) const
{
    NS_LOG_FUNCTION_NOARGS();
    NS_ASSERT(i < 2);
    return m_link[i].m_src;
}

Ptr<NetDevice>
QbbChannel::GetDevice(std::size_t i) const
{
    NS_LOG_FUNCTION_NOARGS();
    return GetQbbDevice(i);
}

Time
QbbChannel::GetDelay() const
{
    return m_delay;
}

Ptr<QbbNetDevice>
QbbChannel::GetSource(uint32_t i) const
{
    return m_link[i].m_src;
}

Ptr<QbbNetDevice>
QbbChannel::GetDestination(uint32_t i) const
{
    return m_link[i].m_dst;
}

bool
QbbChannel::IsInitialized() const
{
    NS_ASSERT(m_link[0].m_state != INITIALIZING);
    NS_ASSERT(m_link[1].m_state != INITIALIZING);
    return true;
}

} // namespace ns3
