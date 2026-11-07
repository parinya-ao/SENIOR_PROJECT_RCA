#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "hello_config.h"
#include "hello_protocol.h"

#define LORA_BUILD_ID "host-test-build"
struct EepromBoundary {
    uint32_t stored = 0xffffffffUL;
    unsigned reads = 0;
    unsigned writes = 0;
    unsigned written_bytes = 0;
    bool wrong_address = false;
    void get(int address, uint32_t& value) {
        wrong_address |= address != 2;
        ++reads; value = stored;
    }
    void put(int address, uint32_t value) {
        wrong_address |= address != 2;
        ++writes; written_bytes += sizeof(value); stored = value;
    }
} EEPROM;
#include "sender_guard_under_test.h"

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); return 1; \
} } while (0)

static bool feed(lora_hello::ControlInput& input, const char* text, uint16_t& session) {
    bool accepted = false;
    uint32_t now = 10;
    while (*text) accepted |= input.feed(*text++, now++, &session);
    return accepted;
}

int main(int argc, char** argv) {
    using namespace lora_hello;
    CHECK(argc == 2);
    ControlInput control('S');
    Campaign campaign(0, 1, true);
    uint16_t session = 0;
    const char* name = argv[1];
    if (!strcmp(name, "first")) {
        CHECK(feed(control, "SA17C", session) && session == 0xa17c);
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(campaign.arm(session) && campaign.start() && campaign.mark_sent());
    } else if (!strcmp(name, "repeat")) {
        CHECK(feed(control, "SA17C", session));
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(!feed(control, "SA17C", session));
        CHECK(!feed(control, "SBEEF", session));
        CHECK(claim_campaign_build() == CampaignBuildGateResult::AlreadyRun);
    } else if (!strcmp(name, "invalid")) {
        CHECK(!feed(control, "S0000", session));
        CHECK(!feed(control, "SZZZZ", session));
        CHECK(!feed(control, "Sa17c", session));
        CHECK(!feed(control, "SA17\n", session));
        CHECK(!feed(control, "R1234", session));
        CHECK(EEPROM.writes == 0 && campaign.state() == State::TEST_IDLE);
        CHECK(feed(control, "SA17C", session));
    } else if (!strcmp(name, "one_attempt")) {
        CHECK(campaign.arm(0xa17c) && campaign.start());
        CHECK(campaign.mark_sent());
        CHECK(!campaign.mark_sent());
        CHECK(campaign.attempts() == 1);
        CHECK(!campaign.timeout());
        CHECK(campaign.state() == State::TEST_FAILED);
        CHECK(!campaign.mark_sent() && !campaign.start() && !campaign.arm(0xbeef));
    } else if (!strcmp(name, "boot")) {
        CHECK(campaign.state() == State::TEST_IDLE);
        CHECK(!campaign.start() && !campaign.mark_sent());
        CHECK(!feed(control, "A17C", session));
        CHECK(campaign.attempts() == 0 && EEPROM.writes == 0);
        CHECK(feed(control, "SA17C", session));
        CHECK(campaign.arm(session) && campaign.start());
    } else if (!strcmp(name, "no_eeprom")) {
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(claim_campaign_build() == CampaignBuildGateResult::AlreadyRun);
        CHECK(EEPROM.reads == 0 && EEPROM.writes == 0 && EEPROM.written_bytes == 0);
    } else if (!strcmp(name, "persistent")) {
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(EEPROM.writes == 1 && EEPROM.written_bytes == 4 && !EEPROM.wrong_address);
        CHECK(claim_campaign_build() == CampaignBuildGateResult::AlreadyRun);
        CHECK(EEPROM.writes == 1);
        Campaign legacy(0, 1, true);
        CHECK(legacy.arm(0xa17c) && legacy.start() && legacy.mark_sent());
        CHECK(legacy.timeout() && legacy.mark_sent());
    } else if (!strcmp(name, "ack")) {
        CHECK(campaign.arm(0xa17c) && campaign.start() && campaign.mark_sent());
        Frame ack{0, 1, 0xa17c, 3, 1};
        for (unsigned field = 0; field < 5; ++field) {
            Frame bad = ack;
            if (field == 0) bad.destination = 1;
            if (field == 1) bad.source = 0;
            if (field == 2) bad.campaign_id = 0xbeef;
            if (field == 3) bad.type = 9;
            if (field == 4) bad.sequence = 2;
            CHECK(!campaign.acknowledge(bad));
        }
        CHECK(campaign.acknowledge(ack));
        CHECK(campaign.state() == State::TEST_COMPLETED && campaign.sequence() == 1);
        CHECK(!campaign.mark_sent() && !campaign.acknowledge(ack));
    } else CHECK(false);
    puts("PASS sender one-shot case");
}
