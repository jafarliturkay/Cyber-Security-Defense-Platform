import nmap

class NetworkScanner:
    def __init__(self):
        self.nm = nmap.PortScanner()

    def scan_target(self, target, ports="21,22,80,443,3306,8080"):
        """
        Belirtilen hedef IP ve portlarda varsayılan Nmap taraması yapar.
        """
        try:
            # -sV: Servis ve versiyon tespiti
            self.nm.scan(hosts=target, ports=ports, arguments='-sV')
            scan_results = []

            for host in self.nm.all_hosts():
                host_info = {
                    'host': host,
                    'status': self.nm[host].state(),
                    'protocols': []
                }
                
                for proto in self.nm[host].all_protocols():
                    lport = self.nm[host][proto].keys()
                    for port in sorted(lport):
                        service = self.nm[host][proto][port]
                        host_info['protocols'].append({
                            'port': port,
                            'name': service.get('name', 'Unknown'),
                            'product': service.get('product', ''),
                            'version': service.get('version', ''),
                            'state': service.get('state', 'Unknown')
                        })
                scan_results.append(host_info)
                
            return True, scan_results
        except Exception as e:
            return False, str(e)