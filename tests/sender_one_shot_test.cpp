#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "hello_config.h"
#include "ssot.h"

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

static bool feed(ssot_control_input_t* input, const char* text, uint16_t& session) {
    bool accepted = false;
    uint32_t now = 10;
    while (*text) accepted |= ssot_control_input_feed(input, *text++, now++, &session);
    return accepted;
}

int main(int argc, char** argv) {
    CHECK(argc == 2);
    ssot_control_input_t control;
    ssot_control_input_init(&control, 'S');
    ssot_campaign_t campaign;
    ssot_campaign_init(&campaign, 0U, 1U, true);
    uint16_t session = 0;
    const char* name = argv[1];
    if (!strcmp(name, "first")) {
        CHECK(feed(&control, "SA17C", session) && session == 0xa17c);
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(ssot_campaign_arm(&campaign, session) &&
              ssot_campaign_start(&campaign) && ssot_campaign_mark_sent(&campaign));
    } else if (!strcmp(name, "repeat")) {
        CHECK(feed(&control, "SA17C", session));
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(!feed(&control, "SA17C", session));
        CHECK(!feed(&control, "SBEEF", session));
        CHECK(claim_campaign_build() == CampaignBuildGateResult::AlreadyRun);
    } else if (!strcmp(name, "invalid")) {
        CHECK(!feed(&control, "S0000", session));
        CHECK(!feed(&control, "SZZZZ", session));
        CHECK(!feed(&control, "Sa17c", session));
        CHECK(!feed(&control, "SA17\n", session));
        CHECK(!feed(&control, "R1234", session));
        CHECK(EEPROM.writes == 0 && campaign.state == SSOT_TEST_IDLE);
        CHECK(feed(&control, "SA17C", session));
    } else if (!strcmp(name, "one_attempt")) {
        CHECK(ssot_campaign_arm(&campaign, 0xa17c) && ssot_campaign_start(&campaign));
        CHECK(ssot_campaign_mark_sent(&campaign));
        CHECK(!ssot_campaign_mark_sent(&campaign));
        CHECK(campaign.attempts == 1U);
        CHECK(!ssot_campaign_timeout(&campaign));
        CHECK(campaign.state == SSOT_TEST_FAILED);
        CHECK(!ssot_campaign_mark_sent(&campaign) && !ssot_campaign_start(&campaign) &&
              !ssot_campaign_arm(&campaign, 0xbeef));
    } else if (!strcmp(name, "boot")) {
        CHECK(campaign.state == SSOT_TEST_IDLE);
        CHECK(!ssot_campaign_start(&campaign) && !ssot_campaign_mark_sent(&campaign));
        CHECK(!feed(&control, "A17C", session));
        CHECK(campaign.attempts == 0U && EEPROM.writes == 0);
        CHECK(feed(&control, "SA17C", session));
        CHECK(ssot_campaign_arm(&campaign, session) && ssot_campaign_start(&campaign));
    } else if (!strcmp(name, "no_eeprom")) {
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(claim_campaign_build() == CampaignBuildGateResult::AlreadyRun);
        CHECK(EEPROM.reads == 0 && EEPROM.writes == 0 && EEPROM.written_bytes == 0);
    } else if (!strcmp(name, "persistent")) {
        CHECK(claim_campaign_build() == CampaignBuildGateResult::Ready);
        CHECK(EEPROM.writes == 1 && EEPROM.written_bytes == 4 && !EEPROM.wrong_address);
        CHECK(claim_campaign_build() == CampaignBuildGateResult::AlreadyRun);
        CHECK(EEPROM.writes == 1);
        ssot_campaign_t legacy;
        ssot_campaign_init(&legacy, 0U, 1U, true);
        CHECK(ssot_campaign_arm(&legacy, 0xa17c) &&
              ssot_campaign_start(&legacy) && ssot_campaign_mark_sent(&legacy));
        CHECK(ssot_campaign_timeout(&legacy) && ssot_campaign_mark_sent(&legacy));
    } else if (!strcmp(name, "ack")) {
        CHECK(ssot_campaign_arm(&campaign, 0xa17c) &&
              ssot_campaign_start(&campaign) && ssot_campaign_mark_sent(&campaign));
        ssot_frame_t ack = {0U, 1U, 0xa17c, 3U, 1U};
        for (unsigned field = 0; field < 5; ++field) {
            ssot_frame_t bad = ack;
            if (field == 0) bad.destination = 1;
            if (field == 1) bad.source = 0;
            if (field == 2) bad.campaign_id = 0xbeef;
            if (field == 3) bad.type = 9;
            if (field == 4) bad.sequence = 2;
            CHECK(!ssot_campaign_acknowledge(&campaign, &bad));
        }
        CHECK(ssot_campaign_acknowledge(&campaign, &ack));
        CHECK(campaign.state == SSOT_TEST_COMPLETED && campaign.sequence == 1U);
        CHECK(!ssot_campaign_mark_sent(&campaign) &&
              !ssot_campaign_acknowledge(&campaign, &ack));
    } else CHECK(false);
    puts("PASS sender one-shot case");
}
