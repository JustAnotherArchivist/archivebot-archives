import datetime
import internetarchive
import logging
import logging.config
import os
import re
import time


def string_to_yaml(s):
	# Convert an arbitrary string for YAML
	return '"{}"'.format(s.replace('\\', '\\\\').replace('"', '\\"')) # Escape backslashes and double quotes, and wrap everything in quotes.


def write_last_update_file(attemptDate, successDate):
	logging.info('Writing last-update file')
	with open(os.path.join(dataDir, 'last-update'), 'w') as fp:
		fp.write('Date of last update attempt:\n')
		fp.write(attemptDate + '\n')
		fp.write('Date of last successful update:\n')
		fp.write(successDate + '\n')


logging.Formatter.converter = time.gmtime
logging.config.dictConfig(
	{
		'version': 1,
		'formatters': {
			'simple': {
				'format': '{asctime} {levelname:<4.4s} {name} {message}',
				'style': '{',
			},
		},
		'handlers': {
			'console': {
				'class': 'logging.StreamHandler',
				'level': 'DEBUG',
				'formatter': 'simple',
				'stream': 'ext://sys.stderr',
			},
		},
		'root': {
			'level': 'DEBUG',
			'handlers': ['console'],
		},
	}
)


dataDir = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/'))
fnPattern = re.compile(r'^.+(-(inf|shallow))?-\d{8}-\d{6}(-\w{5})?.*(\.warc\.gz|\.warc\.os\.cdx\.gz|\.json|-urls\.txt)$') # Based on the one used by the ArchiveBot viewer
	# The identifier part (\w{5}) was not present in the first few items in the collection, so it's optional.
	# Similarly, there are some WARCs in the very first item of the collection (archiveteam_archivebot_go_001) which did not include -inf/shallow, and which used the job ID instead of the domain at the beginning.
datePattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


startDate = datetime.datetime.utcnow().replace(microsecond = 0).isoformat() + 'Z' #TODO: replace .replace().isoformat() with .isoformat(timespec = 'seconds')
assert datePattern.match(startDate)

# Read when the last update attempt/success happened
try:
	with open(os.path.join(dataDir, 'last-update'), 'r') as fp:
		lines = fp.readlines()
	if len(lines) != 4:
		raise ValueError('last-update file has an invalid format: does not contain exactly 4 lines')
	if not 'attempt' in lines[0].lower():
		raise ValueError('last-update file has an invalid format: date of last attempt not found')
	if lines[1].strip() != 'None' and not datePattern.match(lines[1].strip()):
		raise ValueError('last-update file has an invalid format: date of last attempt does not actually look like a date')
	if not 'success' in lines[2].lower():
		raise ValueError('last-update file has an invalid format: date of last success not found')
	if lines[3].strip() != 'None' and not datePattern.match(lines[3].strip()):
		raise ValueError('last-update file has an invalid format: date of last success does not actually look like a date')
	lastAttemptDate = lines[1].strip()
	lastSuccessDate = lines[3].strip()
except FileNotFoundError:
	lastAttemptDate = 'None'
	lastSuccessDate = 'None'

logging.debug('Last attempt: ' + lastAttemptDate)
logging.debug('Last success: ' + lastSuccessDate)

# Ensure that the target directories exist
os.makedirs(os.path.join(dataDir, 'items'), exist_ok = True)

# Update last-update file with the current attempt
write_last_update_file(attemptDate = startDate, successDate = lastSuccessDate)

# Go!
query = 'collection:archivebot'
if lastSuccessDate != 'None':
	query += ' oai_updatedate:[' + lastSuccessDate + ' TO null]'
logging.info('Query: {!r}'.format(query))
for i in internetarchive.search_items(query, request_kwargs = {'timeout': 60}).iter_as_items(): #TODO: add max_retries
	logging.info('Processing item {}'.format(i.identifier))
	with open(os.path.join(dataDir, 'items', '{}.yaml'.format(i.identifier)), 'w') as fp:
		for f in i.files:
			if fnPattern.match(f['name']):
				if 'size' not in f: # Might happen, e.g. for items which are currently being derived
					logging.error('Size of {} is missing'.format(f['name']))
					size = None
				else:
					if not f['size'].isdigit():
						logging.error('Size of {} invalid: {!r} is not a positive integer'.format(f['name'], f['size']))
						size = None
					else:
						size = int(f['size'])
				if 'mtime' not in f: # As above
					logging.error('Mtime of {} is missing'.format(f['name']))
					size = None
				else:
					if not f['mtime'].isdigit():
						logging.error('Mtime of {} invalid: {!r} is not a positive integer'.format(f['name'], f['mtime']))
						mtime = None
					else:
						mtime = int(f['mtime'])
				fp.write('{}: {{size: {}, mtime: {}}}\n'.format(string_to_yaml(f['name']), size, mtime))
			elif not f['name'].endswith('.cdx.gz'):
				logging.info('Skipping {}'.format(f['name']))

# If we end up here, the update was successful; write the last-update file
write_last_update_file(attemptDate = startDate, successDate = startDate)

logging.info('Done')
