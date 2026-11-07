"""Generate deterministic diagnostic headers and manifest."""
import argparse
import hashlib
import json
from validate_lora_ssot import ROOT, load, validate


def source_fingerprint():
    paths = list((ROOT / 'src').rglob('*')) + list((ROOT / 'tools/config').glob('*.py'))
    paths += [ROOT / 'platformio.ini']
    # Include the direct integration sources used by PlatformIO symlink libraries.
    for directory in ('lib', 'include'):
        paths += list((ROOT.parent / 'iwing-tracker/device-lora_dev' / directory).rglob('*'))
    integration = ROOT.parent / 'iwing-tracker/device-lora_dev'
    return digest({('project/' + str(path.relative_to(ROOT)) if path.is_relative_to(ROOT)
                    else 'integration/' + str(path.relative_to(integration))): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(paths) if path.is_file() and path.suffix in ('.h', '.c', '.cpp', '.py', '.ini')})


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def artifacts(config):
    validate(config)
    shared = {key: config[key] for key in ('schema_version', 'radio', 'protocol', 'timeouts', 'retries')}
    fingerprint = digest(shared)
    manifest = dict(shared=shared, shared_fingerprint=fingerprint, boards={}, environments={})
    source_hash = source_fingerprint()
    manifest['source_fingerprint'] = source_hash
    macros = {'FREQUENCY_MHZ': 'frequency_mhz', 'TX_POWER_DBM': 'tx_power_dbm',
              'SPREADING_FACTOR': 'spreading_factor', 'BANDWIDTH_KHZ': 'bandwidth_khz',
              'CODING_RATE': 'coding_rate', 'SYNC_WORD': 'sync_word',
              'PREAMBLE_SYMBOLS': 'preamble_symbols', 'CRC_ENABLED': 'crc_enabled',
              'IQ_INVERTED': 'iq_inverted'}
    lines = ['#pragma once', '// Generated from config/lora_system.json.']
    for macro, key in macros.items():
        value = config['radio'][key]
        if isinstance(value, bool):
            value = int(value)
        if key == 'frequency_mhz':
            value = f'{float(value)}f'
        lines.extend([f'#ifdef HELLO_RF_{macro}', f'static_assert(HELLO_RF_{macro} == {value}, "Conflicting {macro}; use SSOT");', '#else', f'#define HELLO_RF_{macro} {value}', '#endif'])
    lines += ['#define HELLO_RF_LONG_RANGE 0', f'#define LORA_CONFIG_FINGERPRINT "{fingerprint}"',
              f'#define LORA_PROTOCOL_VERSION {config["protocol"]["version"]}',
              f'#define LORA_PROTOCOL_VERSION_TEXT "{config["protocol"]["version"]}"',
              f'#define LORA_MAX_RETRIES {config["retries"]["max_retries"]}',
              f'#define LORA_HELLO_PAYLOAD "{config["protocol"]["payload"]}"',
              f'#define LORA_ACK_TIMEOUT_MS {config["timeouts"]["ack_ms"]}',
              f'#define LORA_TX_TIMEOUT_MS {config["timeouts"]["tx_ms"]}']
    for name in ('sender_address', 'receiver_address', 'sequence', 'data_type', 'ack_type', 'nack_type'):
        lines.append(f'#define LORA_{name.upper()} {config["protocol"][name]}')
    outputs = {'include/generated/lora_shared_config.h': '\n'.join(lines) + '\n'}
    layout = ['[target_layout]']
    for role, target in [('sender', 'gateway'), ('receiver', 'receiver')]:
        board = config[f'{role}_board']
        for key in ('bootsize', 'codesize', 'bodcfg'):
            layout.append(f'{target}_{key} = {hex(board[key])}')
        layout.append(f'{target}_app_start = {hex(board["image_start"])}')
    layout += ['[flash_geometry]', 'total_bytes = 131072',
               f'application_end = {hex(config["receiver_board"]["image_end_exclusive"])}']
    outputs['generated/lora_platformio.ini'] = '\n'.join(layout) + '\n'
    for role in ('sender', 'receiver'):
        board = config[f'{role}_board']
        full = digest(dict(shared=shared, board=board, role=role))
        manifest['boards'][role] = dict(board, build_fingerprint=full)
        lines = ['#pragma once', '// Generated from config/lora_system.json.',
                 f'#define LORA_BUILD_FINGERPRINT "{full}"',
                 f'#define LORA_IMAGE_START {board["image_start"]}',
                 f'#define LORA_IMAGE_END {board["image_end_exclusive"]}']
        lines.append(f'#define LORA_SPI_ROUTE {board["spi_route"]}')
        if role == 'receiver':
            lines.append(f'#define LORA_POWER_ACTIVE_LEVEL {board["radio_power_active_level"]}')
        for name, pin in board['pins'].items():
            lines.append(f'#define LORA_PIN_{name.upper()} PIN_{pin}')
        outputs[f'include/generated/lora_{role}_board.h'] = '\n'.join(lines) + '\n'
    for environment in ('sender', 'sender_hello', 'receiver', 'sender_hello_spi', 'receiver_spi'):
        role = 'receiver' if environment.startswith('receiver') else 'sender'
        manifest['environments'][environment] = dict(
            role=role, build_id=digest(dict(environment=environment, source=source_hash,
                                          board=manifest['boards'][role]['build_fingerprint'])))
    outputs['generated/lora_manifest.json'] = json.dumps(manifest, sort_keys=True, indent=2) + '\n'
    return outputs


def generate(check=False):
    for name, contents in artifacts(load(ROOT / 'config/lora_system.json')).items():
        path = ROOT / name
        if check:
            if not path.is_file() or path.read_text() != contents:
                raise ValueError(f'stale generated artifact: {name}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text() != contents:
                path.write_text(contents)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        generate(args.check)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
