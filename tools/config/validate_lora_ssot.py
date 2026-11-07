"""Strict diagnostic configuration validation; physical inventory is not inferred."""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate key: {key}')
        result[key] = value
    return result


def validate(config):
    board_shape = dict(mcu='', bootsize=0, codesize=0, bodcfg=0, image_start=0,
                       image_end_exclusive=0, spi_route='',
                       pins=dict.fromkeys(('mosi', 'miso', 'sck', 'cs', 'rst', 'irq', 'dio1'), ''))
    receiver_shape = dict(board_shape, radio_power_active_level=0,
                          pins=dict(board_shape['pins'], enable='', sd_cs='', led1='', led2='',
                                    gps_enable='', sd_enable='', sd_detect=''))
    reference = dict(schema_version=0,
        experiment=dict(mode='', radio_inventory=None, antenna_inventory=None),
        radio=dict(frequency_mhz=0.0, tx_power_dbm=0, spreading_factor=0,
                   bandwidth_khz=0, coding_rate=0, sync_word=0,
                   preamble_symbols=0, crc_enabled=True,
                   explicit_header=True, iq_inverted=False),
        protocol=dict(version=0, encoding='', sender_address=0, receiver_address=0, data_type=0, ack_type=0, nack_type=0,
                      sequence_bits=0, sequence=0, payload=''),
        sender_board=board_shape, receiver_board=receiver_shape,
        timeouts=dict(ack_ms=0, tx_ms=0), retries=dict(max_retries=0))
    def shape(value, expected, path):
        if isinstance(expected, dict):
            if not isinstance(value, dict) or value.keys() != expected.keys():
                raise ValueError(f'{path}: missing or unknown fields')
            for key in expected:
                shape(value[key], expected[key], f'{path}.{key}')
        elif expected is not None and type(value) is not type(expected):
            if not (type(expected) is float and type(value) in (int, float)):
                raise ValueError(f'{path}: invalid type')
    shape(config, reference, 'config')
    if config['schema_version'] != 1:
        raise ValueError('unsupported schema_version')
    radio = config['radio']
    for key, low, high in [('frequency_mhz', 920, 925), ('tx_power_dbm', 2, 20)]:
        if not math.isfinite(radio[key]) or not low <= radio[key] <= high:
            raise ValueError(f'radio.{key}: out of candidate range')
    required = {'spreading_factor': 7, 'bandwidth_khz': 125, 'coding_rate': 5,
                'sync_word': 18, 'preamble_symbols': 8, 'crc_enabled': True,
                'explicit_header': True, 'iq_inverted': False}
    for key, value in required.items():
        if radio[key] != value:
            raise ValueError(f'radio.{key}: unsupported diagnostic setting')
    protocol = config['protocol']
    if protocol != {'version': 2, 'encoding': 'existing_radio_header',
                    'sender_address': 0, 'receiver_address': 1,
                    'data_type': 8, 'ack_type': 3, 'nack_type': 9,
                    'sequence_bits': 8, 'sequence': 1, 'payload': 'hello world'}:
        raise ValueError('unsupported protocol framing or payload')
    for role, boot in [('sender', 0), ('receiver', 44)]:
        board = config[f'{role}_board']
        board_without_pins = {key: value for key, value in board.items() if key != 'pins'}
        expected = dict(mcu='AVR128DA28', bootsize=boot, codesize=0, bodcfg=0 if role == 'sender' else 84,
                         image_start=boot * 512, image_end_exclusive=130048,
                         spi_route='SPI1_SWAP_DEFAULT')
        pins = dict(mosi='PC0', miso='PC1', sck='PC2', cs='PC3')
        controls = ('PD0', 'PD2', 'PD3', 'PD4', 'PD5', 'PD6', 'PD7')
        if role == 'receiver':
            expected['radio_power_active_level'] = 0
            pins.update(cs='PD0', enable='PA7', sd_cs='PC3', led1='PA6', led2='PA5',
                        gps_enable='PD5', sd_enable='PD6', sd_detect='PA4')
            controls = ('PD1', 'PD2', 'PD3', 'PD4', 'PD5', 'PD6', 'PD7')
        if board_without_pins != expected:
            raise ValueError(f'{role}: unsupported board geometry or pin mapping')
        if any(board['pins'][name] != pin for name, pin in pins.items()) or \
                any(board['pins'][name] not in controls for name in ('rst', 'irq', 'dio1')) or \
                len(set(board['pins'].values())) != len(board['pins']):
            raise ValueError(f'{role}: invalid or overlapping SPI1/radio pins')
    if config['experiment'] != dict(mode='single_packet', radio_inventory=None, antenna_inventory=None):
        raise ValueError('experiment: unsupported mode or unverified inventory assertion')
    if not all(100 <= value <= 60000 for value in config['timeouts'].values()):
        raise ValueError('timeouts out of range')
    if not 0 <= config['retries']['max_retries'] <= 3:
        raise ValueError('retry limit out of range')
    return config


def load(path):
    return validate(json.loads(Path(path).read_text(), object_pairs_hook=unique_object))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', type=Path, default=ROOT / 'config/lora_system.json')
    args = parser.parse_args()
    try:
        load(args.path)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Invalid LoRa SSOT: {error}\n')
    print('LoRa SSOT valid (physical suitability remains unverified)')


if __name__ == '__main__':
    main()
