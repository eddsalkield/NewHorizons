def normalise_url_protocol(url):
	if url.startswith("//"):
		url = "https:" + url
	return url
