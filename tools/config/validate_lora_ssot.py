"""Strict diagnostic configuration validation; physical inventory is not inferred."""
import argparse
import json
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
                       image_end_exclusive=0)
    receiver_shape = dict(board_shape,
                          pins=dict(sd_cs='', led1='', led2='', gps_enable='',
                                    sd_enable='', sd_detect=''))
    reference = dict(schema_version=0,
        experiment=dict(mode='', radio_inventory=None, antenna_inventory=None),
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
    protocol = config['protocol']
    if protocol != {'version': 2, 'encoding': 'existing_radio_header',
                    'sender_address': 0, 'receiver_address': 1,
                    'data_type': 8, 'ack_type': 3, 'nack_type': 9,
                    'sequence_bits': 8, 'sequence': 1, 'payload': 'hello world'}:
        raise ValueError('unsupported protocol framing or payload')
    for role, boot in [('sender', 0), ('receiver', 0)]:
        board = config[f'{role}_board']
        expected = dict(mcu='AVR128DA28', bootsize=boot, codesize=0, bodcfg=0,
                        image_start=boot * 512, image_end_exclusive=130048)
        if role == 'receiver':
            expected['pins'] = dict(sd_cs='PC3', led1='PA6', led2='PA5',
                                    gps_enable='PD5', sd_enable='PD6', sd_detect='PA4')
        if board != expected:
            raise ValueError(f'{role}: unsupported board geometry or pin mapping')
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
