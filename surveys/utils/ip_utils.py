# utils/ip_utils.py
def get_client_ip(request):
	"""
	Get the client's real IP address from Django request.
	Handles proxies, load balancers, and various HTTP headers.
	"""
	# Try common proxy headers (in order of reliability)
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	
	if x_forwarded_for:
		# HTTP_X_FORWARDED_FOR can contain multiple IPs in a chain: client, proxy1, proxy2
		# The first IP is the original client
		ip_list = x_forwarded_for.split(',')
		client_ip = ip_list[0].strip()
		return client_ip
	
	# Other common headers (used by different proxies/CDNs)
	headers_to_check = [
		'HTTP_X_REAL_IP',
		'HTTP_CLIENT_IP',
		'HTTP_X_FORWARDED',
		'HTTP_X_CLUSTER_CLIENT_IP',
		'HTTP_FORWARDED_FOR',
		'HTTP_FORWARDED',
		'HTTP_CF_CONNECTING_IP',  # Cloudflare
		'HTTP_TRUE_CLIENT_IP',    # Akamai, Cloudflare
	]
	
	for header in headers_to_check:
		ip = request.META.get(header)
		if ip:
			# Clean up if there are multiple IPs
			if ',' in ip:
				ip = ip.split(',')[0].strip()
			return ip
	
	# Fallback to REMOTE_ADDR (direct connection)
	remote_addr = request.META.get('REMOTE_ADDR')
	if remote_addr:
		return remote_addr
	
	# Last resort
	return request.META.get('REMOTE_HOST', '0.0.0.0')