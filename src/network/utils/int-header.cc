#include "int-header.h"

namespace ns3 {

const uint64_t IntHop::lineRateValues[8] = {25000000000lu,50000000000lu,100000000000lu,200000000000lu,400000000000lu,0,0,0};
uint32_t IntHop::multi = 1;

IntHeader::Mode IntHeader::mode = NONE;
int IntHeader::pint_bytes = 2;

IntHeader::IntHeader() : nhop(0) {
	for (uint32_t i = 0; i < maxHop; i++)
		hop[i] = {0};
}

uint32_t IntHeader::GetStaticSize(){
	if (mode == NORMAL || mode == FSMIX){   // FSMIX shares NORMAL's 42-byte wire layout
		return sizeof(hop) + sizeof(nhop);
	}else if (mode == TS){
		return sizeof(ts);
	}else if (mode == PINT){
		return sizeof(pint);
	}else if (mode == FS){
		return sizeof(fairRate);
	}else {
		return 0;
	}
}

void IntHeader::PushHop(uint64_t time, uint64_t bytes, uint32_t qlen, uint64_t rate){
	// only do this in INT mode (FSMIX carries the same per-hop record for its stock-HPCC class)
	if (mode == NORMAL || mode == FSMIX){
		uint32_t idx = nhop % maxHop;
		hop[idx].Set(time, bytes, qlen, rate);
		nhop++;
	}
}

void IntHeader::Serialize (Buffer::Iterator start) const{
	Buffer::Iterator i = start;
	if (mode == NORMAL || mode == FSMIX){
		for (uint32_t j = 0; j < maxHop; j++){
			i.WriteU32(hop[j].buf[0]);
			i.WriteU32(hop[j].buf[1]);
		}
		i.WriteU16(nhop);
	}else if (mode == TS){
		i.WriteU64(ts);
	}else if (mode == PINT){
		if (pint_bytes == 1)
			i.WriteU8(pint.power_lo8);
		else if (pint_bytes == 2)
			i.WriteU16(pint.power);
	}else if (mode == FS){
		i.WriteU64(fairRate);
	}
}

uint32_t IntHeader::Deserialize (Buffer::Iterator start){
	Buffer::Iterator i = start;
	if (mode == NORMAL || mode == FSMIX){
		for (uint32_t j = 0; j < maxHop; j++){
			hop[j].buf[0] = i.ReadU32();
			hop[j].buf[1] = i.ReadU32();
		}
		nhop = i.ReadU16();
	}else if (mode == TS){
		ts = i.ReadU64();
	}else if (mode == PINT){
		if (pint_bytes == 1)
			pint.power_lo8 = i.ReadU8();
		else if (pint_bytes == 2)
			pint.power = i.ReadU16();
	}else if (mode == FS){
		fairRate = i.ReadU64();
	}
	return GetStaticSize();
}

uint64_t IntHeader::GetTs(void){
	if (mode == TS)
		return ts;
	return 0;
}

uint16_t IntHeader::GetPower(void){
	if (mode == PINT)
		return pint_bytes == 1 ? pint.power_lo8 : pint.power;
	return 0;
}
void IntHeader::SetPower(uint16_t power){
	if (mode == PINT){
		if (pint_bytes == 1)
			pint.power_lo8 = power;
		else
			pint.power = power;
	}
}

uint64_t IntHeader::GetFairRate(void){
	// In FSMIX the fair rate occupies the union's first 8 bytes (== hop[0].buf); the FS-class
	// packets that use it never push hop records, so the alias is unambiguous.
	if (mode == FS || mode == FSMIX)
		return fairRate;
	return 0;
}
void IntHeader::SetFairRate(uint64_t r){
	if (mode == FS || mode == FSMIX)
		fairRate = r;
}

}
