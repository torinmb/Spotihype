import sys, json
import urllib, urllib2, json
import time, exceptions, ssl
from concurrent import futures

def get_user_songs(username, favorites_count):
	base_url= 'https://api.hypem.com/v2/users/'+username+'/favorites?&key=swagger&count='
	total_page_count = 1
	if favorites_count > 3600:
		total_page_count = math.ceil(favorites_count / 3600.0)

	with futures.ProcessPoolExecutor(max_workers=total_page_count) as executor:
		pool = []
		progress = 0
		for i in xrange(1, total_page_count + 1):
			user_url = ''

			if total_page_count != 1:
				user_url = base_url + '3600&page=' + str(i)
			else:
				user_url = base_url + str(favorites_count) + '&page=1'
			job = executor.submit(get_hypem_tracks, user_url, (i - 1))
			pool.append(job)

		results = [None for i in xrange(total_page_count)]
		
		for job in futures.as_completed(pool):
			href, i = job.result()
			results[i] = href

		spotify_hrefs = []
		for r in results:
			spotify_hrefs += r

		print '\n\nCopy and paste into a spotify playlist:\n'
		for url in spotify_hrefs:
			if url != None:
				print url 
			
def get_hypem_tracks(url, track_index):
	data = safeGet(url)
	if type(data) == urllib2.HTTPError or type(data) == ssl.SSLError:
		print "error Retrieving Hypem data"
	else:
		with futures.ProcessPoolExecutor(max_workers=20) as executor:
			pool = []
			progress = 0
			data = json.loads(data.read())
			results = [None for i in xrange(len(data))]
			for i, curr_song in enumerate(data):
				job = executor.submit(get_spotify_song, curr_song['title'], i-1)
				pool.append(job)

			for job in futures.as_completed(pool):
				href, index = job.result()
				results[index] = href
				progress += 1
				update_progress(1.0 * progress / len(data))
			return results, track_index
	return [], track_index


def get_spotify_song(song, i):
	try:
		query = urllib.urlencode({'q': song})
	except:
		print "error encoding" + song
		return None, i

	curr_song = json.loads(safeGet('http://ws.spotify.com/search/1/track.json?' + query).read())
	if curr_song['info']['num_results']:
		return curr_song['tracks'][0]['href'], i
	else:
		print song + ' not found'
	return None, i

def update_progress(progress):
	width = 40
	curr = int(progress * width)
	bar = '=' * curr
	spaces = ' ' * (width - curr)
	sys.stdout.write('\r[{0}{1}] {2}% '.format(bar, spaces, int(progress * 100)))
	sys.stdout.flush()

def safeGet(url):
	server_request_delay = 0
	while server_request_delay < 10:
		try:
			return urllib2.urlopen(url, timeout=60)
		except Exception, data:
			print "exception", data, 'Url:', url
			if type(data) == urllib2.HTTPError or type(data) == ssl.SSLError:
				server_request_delay += 1
				print "sleeping for %d seconds"%(server_request_delay * 15)
				time.sleep(15 * server_request_delay)
			else:
				return None
	print "Error Tried 10 Times"
	return None

if __name__ == '__main__':
	try:
		username = sys.argv[1]
		user_data = json.loads(urllib2.urlopen('https://api.hypem.com/v2/users?q=' + username + '&key=swagger', timeout=60).read())
		if user_data:
			favorites_count = user_data[0]['favorites_count']['item']
			get_user_songs(username, favorites_count)
		else:
			print 'Please provide a valid hypem username'
	except:
		print 'Please provide a Hypem username'
		print 'Usage: python Spotihype.py hypem_user_name'
