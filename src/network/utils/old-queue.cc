/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007 University of Washington
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
#include <stdio.h>
#include "ns3/log.h"
#include "ns3/trace-source-accessor.h"
#include "old-queue.h"

NS_LOG_COMPONENT_DEFINE ("OldQueue");

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (OldQueue);

TypeId
OldQueue::GetTypeId (void)
{
    static TypeId tid = TypeId ("ns3::OldQueue")
                            .SetParent<Object> ()
                            .AddTraceSource ("Enqueue", "Enqueue a packet in the queue.",
                                            MakeTraceSourceAccessor (&OldQueue::m_traceEnqueue),
                                            "ns3::Packet::TracedCallback")
                            .AddTraceSource ("Dequeue", "Dequeue a packet from the queue.",
                                            MakeTraceSourceAccessor (&OldQueue::m_traceDequeue),
                                            "ns3::Packet::TracedCallback")
                            .AddTraceSource ("Drop", "Drop a packet stored in the queue.",
                                            MakeTraceSourceAccessor (&OldQueue::m_traceDrop),
                                            "ns3::Packet::TracedCallback")
        ;
    return tid;
}

OldQueue::OldQueue() :
      m_nBytes (0),
      m_nTotalReceivedBytes (0),
      m_nPackets (0),
      m_nTotalReceivedPackets (0),
      m_nTotalDroppedBytes (0),
      m_nTotalDroppedPackets (0)
{
    NS_LOG_FUNCTION_NOARGS ();
}

OldQueue::~OldQueue()
{
    NS_LOG_FUNCTION_NOARGS ();
}


bool
OldQueue::Enqueue (Ptr<Packet> p)
{
    NS_LOG_FUNCTION (this << p);

    //
    // If DoEnqueue fails, OldQueue::Drop is called by the subclass
    //
    bool retval = DoEnqueue (p);
    if (retval)
    {
        NS_LOG_LOGIC ("m_traceEnqueue (p)");
        m_traceEnqueue (p);

        uint32_t size = p->GetSize ();
        m_nBytes += size;
        m_nTotalReceivedBytes += size;

        m_nPackets++;
        m_nTotalReceivedPackets++;
    }
    return retval;
}

Ptr<Packet>
OldQueue::Dequeue (void)
{
    NS_LOG_FUNCTION (this);

    //printf("dequeue!!\n");
    //fflush(stdout);

    Ptr<Packet> packet = DoDequeue ();

    if (packet)
    {
        NS_ASSERT (m_nBytes >= packet->GetSize ());
        NS_ASSERT (m_nPackets > 0);

        m_nBytes -= packet->GetSize ();
        m_nPackets--;

        NS_LOG_LOGIC ("m_traceDequeue (packet)");
        m_traceDequeue (packet);
    }
    return packet;
}

void
OldQueue::DequeueAll (void)
{
    NS_LOG_FUNCTION (this);
    while (!IsEmpty ())
    {
        Dequeue ();
    }
}

Ptr<const Packet>
OldQueue::Peek (void) const
{
    NS_LOG_FUNCTION (this);
    return DoPeek ();
}


uint32_t
OldQueue::GetNPackets (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC ("returns " << m_nPackets);
    return m_nPackets;
}

uint32_t
OldQueue::GetNBytes (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC (" returns " << m_nBytes);
    return m_nBytes;
}

bool
OldQueue::IsEmpty (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC ("returns " << (m_nPackets == 0));
    return m_nPackets == 0;
}

uint32_t
OldQueue::GetTotalReceivedBytes (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC ("returns " << m_nTotalReceivedBytes);
    return m_nTotalReceivedBytes;
}

uint32_t
OldQueue::GetTotalReceivedPackets (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC ("returns " << m_nTotalReceivedPackets);
    return m_nTotalReceivedPackets;
}

uint32_t
OldQueue:: GetTotalDroppedBytes (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC ("returns " << m_nTotalDroppedBytes);
    return m_nTotalDroppedBytes;
}

uint32_t
OldQueue::GetTotalDroppedPackets (void) const
{
    NS_LOG_FUNCTION_NOARGS ();
    NS_LOG_LOGIC ("returns " << m_nTotalDroppedPackets);
    return m_nTotalDroppedPackets;
}

void
OldQueue::ResetStatistics (void)
{
    NS_LOG_FUNCTION_NOARGS ();
    m_nTotalReceivedBytes = 0;
    m_nTotalReceivedPackets = 0;
    m_nTotalDroppedBytes = 0;
    m_nTotalDroppedPackets = 0;
}

void
OldQueue::Drop (Ptr<Packet> p)
{
    NS_LOG_FUNCTION (this << p);

    m_nTotalDroppedPackets++;
    m_nTotalDroppedBytes += p->GetSize ();

    NS_LOG_LOGIC ("m_traceDrop (p)");
    m_traceDrop (p);
}

} // namespace ns3
