# ==============================================================================
# ESP-ClimateNode: Lightweight UDP DNS Captive / Name Resolution Server
# ==============================================================================
# Intercepts DNS queries on UDP port 53 and resolves custom local domain names
# (e.g. climate.local, esp.local) and wildcard queries to the SoftAP IP.
# Enables friendly domain navigation and automatic captive portal triggers on
# iOS, Android, macOS, and Windows.
# ==============================================================================

import usocket as socket
import gc

class DNSServer:
    """
    Cooperative, non-blocking RFC 1035 UDP DNS Server.
    Maps custom local domains and captive portal probes to the SoftAP gateway IP.
    """

    def __init__(self, ip="192.168.4.1", port=53):
        self.ip = ip
        self.ip_bytes = bytes([int(part) for part in ip.split(".")])
        self.port = port
        self.sock = None
        self._init_socket()

    def _init_socket(self):
        """Initializes non-blocking UDP socket on port 53."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.port))
            self.sock.setblocking(False)
            print(" [DNS] Captive DNS Server listening on UDP port {}".format(self.port))
        except Exception as e:
            print(" [DNS-WARN] Failed to bind DNS socket on port {}: {}".format(self.port, e))
            self.sock = None

    def process(self):
        """
        Processes pending DNS queries in non-blocking mode.
        Returns immediately if no packets are waiting in the socket buffer.
        """
        if not self.sock:
            return

        try:
            data, addr = self.sock.recvfrom(256)
            if not data or len(data) < 12:
                return

            # Extract Transaction ID and Questions count
            tid = data[:2]
            qdcount = data[4:6]

            # Parse QNAME in Question Section (labels delimited by length byte, ending in 0x00)
            idx = 12
            while idx < len(data) and data[idx] != 0:
                idx += 1 + data[idx]
            idx += 5  # 1 byte (null) + 2 bytes (QTYPE) + 2 bytes (QCLASS)

            if idx > len(data):
                return

            question = data[12:idx]

            # RFC 1035 Standard DNS Response:
            # - Header: Flags = 0x8180 (Response, Opcode=0, Authoritative, No Error)
            # - Question: Echoed directly from request
            # - Answer: Compression pointer to QNAME (0xc00c), Type A (0x0001),
            #           Class IN (0x0001), TTL 60s (0x0000003c), Data Len 4 (0x0004), 4-byte IP
            response = (
                tid +
                b"\x81\x80" +
                qdcount +
                b"\x00\x01\x00\x00\x00\x00" +
                question +
                b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00<\x00\x04" +
                self.ip_bytes
            )

            self.sock.sendto(response, addr)

        except OSError:
            # Socket buffer empty (non-blocking) - normal behavior
            pass
        except Exception:
            pass

    def close(self):
        """Closes the UDP socket safely."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

