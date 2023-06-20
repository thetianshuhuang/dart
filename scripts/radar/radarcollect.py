#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import subprocess
import time
import numpy as np
import os
import socket
import struct
import tables as tb


CMD_DIR = 'C:/ti/mmwave_studio_02_01_01_00/mmWaveStudio/RunTime'
SCRIPT_FILE = 'C:/Users/Administrator/git/dart/scripts/radar/Automation.lua'
PACKET_BUFSIZE = 8192
MAX_PACKET_SIZE = 4096


class Packet(tb.IsDescription):
    t           = tb.Float64Col()
    packet_data = tb.UInt16Col(shape=(728,))
    packet_num  = tb.UInt32Col()
    byte_count  = tb.UInt64Col()


def add_args(parser):
    parser.add_argument(
        '--static_ip', '-i',
        help='Static IP address (eg 192.168.33.30)',
        default='192.168.33.30'
    )
    parser.add_argument(
        '--data_port', '-d',
        help='Port for data stream (eg. 4098)',
        type=int,
        default=4098
    )
    parser.add_argument(
        '--config_port', '-c',
        help='Port for config stream (eg. 4096)',
        type=int,
        default=4096
    )
    parser.add_argument(
        '--timeout', '-t',
        help='Socket timeout in seconds (eg. 20)',
        type=float,
        default=20
    )


def radarcollect(args):
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    outfile = os.path.join(args.output, 'radarpackets.h5')

    cwd = os.getcwd()
    os.chdir(CMD_DIR)
    subprocess.Popen(['mmWaveStudio.exe', '/lua', SCRIPT_FILE])
    os.chdir(cwd)
    print('waiting 56 seconds...')
    time.sleep(56.0)
    print('starting!')

    cfg_recv = (args.static_ip, args.config_port)
    data_recv = (args.static_ip, args.data_port)

    # Create sockets
    config_socket = socket.socket(socket.AF_INET,
                                  socket.SOCK_DGRAM,
                                  socket.IPPROTO_UDP)
    data_socket = socket.socket(socket.AF_INET,
                                socket.SOCK_DGRAM,
                                socket.IPPROTO_UDP)
    data_socket.setblocking(False)

    # Bind data socket to fpga
    data_socket.bind(data_recv)

    # Bind config socket to fpga
    config_socket.bind(cfg_recv)

    # Configure
    data_socket.settimeout(args.timeout)

    with tb.open_file(outfile, mode='w', title='Packet file') as h5file:
        scan_group = h5file.create_group('/', 'scan', 'Scan information')
        packet_table = h5file.create_table(scan_group, 'packet', Packet, 'Packet data')
        packet_in_chunk = 0
        num_all_packets = 0
        start_time = time.time()
        try:
            while True:
                packet_num, byte_count, packet_data = _read_data_packet(data_socket)
                curr_time = time.time()
                packet_table.row['t'] = curr_time
                packet_table.row['packet_data'] = packet_data
                packet_table.row['packet_num'] = packet_num
                packet_table.row['byte_count'] = byte_count
                packet_table.row.append()
                packet_in_chunk += 1
                num_all_packets += 1
                if packet_in_chunk >= PACKET_BUFSIZE:
                    print(f'Flushing {packet_in_chunk} packets.')
                    print(f'Capture time: {curr_time - start_time}s\n')
                    packet_table.flush()
                    packet_in_chunk = 0

        except (KeyboardInterrupt, Exception) as e:
            print(e)

        curr_time = time.time()
        print(f'Flushing {packet_in_chunk} packets.')
        print(f'Capture time: {curr_time - start_time}s\n')
        print("Total packets captured ", num_all_packets)
        packet_table.flush()
        packet_in_chunk = 0
        data_socket.close()
        config_socket.close()


def _read_data_packet(data_socket):
    """Helper function to read in a single ADC packet via UDP

    Returns:
        Current packet number, byte count of data that has already been read, raw ADC data in current packet

    """
    hit_timeout = False
    while True:
        try:
            data = data_socket.recv(MAX_PACKET_SIZE)
            if not hit_timeout:
                print("Busy-wait did not spin at least once; "
                      "possible deadline miss.")
            break
        except socket.timeout:
            hit_timeout = True

    packet_num = struct.unpack('<1l', data[:4])[0]
    byte_count = struct.unpack('>Q', b'\x00\x00' + data[4:10][::-1])[0]
    packet_data = np.frombuffer(data[10:], dtype=np.uint16)
    return packet_num, byte_count, packet_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_args(parser)
    parser.add_argument(
        '--output', '-o',
        help='Output directory (eg. C:/Users/Administrator/Desktop/dartdata/dataset0',
        default='./'
    )
    args = parser.parse_args()
    radarcollect(args)
