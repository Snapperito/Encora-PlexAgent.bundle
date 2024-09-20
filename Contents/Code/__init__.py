# -*- coding: utf-8 -*-

### Imports ###
import sys                  # getdefaultencoding, getfilesystemencoding, platform, argv
import os                   # path.abspath, join, dirname
import re                   #
import inspect              # getfile, currentframe
import urllib2              #
from   lxml    import etree #
from   io      import open  # open
import hashlib

###Mini Functions ###
def natural_sort_key     (s):  return [int(text) if text.isdigit() else text for text in re.split(re.compile('([0-9]+)'), str(s).lower())]  ### Avoid 1, 10, 2, 20... #Usage: list.sort(key=natural_sort_key), sorted(list, key=natural_sort_key)
def sanitize_path        (p):  return p if isinstance(p, unicode) else p.decode(sys.getfilesystemencoding()) ### Make sure the path is unicode, if it is not, decode using OS filesystem's encoding ###
def js_int               (i):  return int(''.join([x for x in list(i or '0') if x.isdigit()]))  # js-like parseInt - https://gist.github.com/douglasmiranda/2174255

### Return dict value if all fields exists "" otherwise (to allow .isdigit()), avoid key errors
def Dict(var, *arg, **kwarg):  #Avoid TypeError: argument of type 'NoneType' is not iterable
  """ Return the value of an (imbricated) dictionnary, return "" if doesn't exist unless "default=new_value" specified as end argument
      Ex: Dict(variable_dict, 'field1', 'field2', default = 0)
  """
  for key in arg:
    if isinstance(var, dict) and key and key in var or isinstance(var, list) and isinstance(key, int) and 0<=key<len(var):  var = var[key]
    else:  return kwarg['default'] if kwarg and 'default' in kwarg else ""   # Allow Dict(var, tvdbid).isdigit() for example
  return kwarg['default'] if var in (None, '', 'N/A', 'null') and kwarg and 'default' in kwarg else "" if var in (None, '', 'N/A', 'null') else var

### Get media directory ###
def GetMediaDir (media, movie, file=False):
  if movie:  return os.path.dirname(media.items[0].parts[0].file)
  else:
    for s in media.seasons if media else []: # TV_Show:
      for e in media.seasons[s].episodes:
        Log.Info(media.seasons[s].episodes[e].items[0].parts[0].file)
        return media.seasons[s].episodes[e].items[0].parts[0].file if file else os.path.dirname(media.seasons[s].episodes[e].items[0].parts[0].file)

### Get media root folder ###
def GetLibraryRootPath(dir):
  library, root, path = '', '', ''
  for root in [os.sep.join(dir.split(os.sep)[0:x+2]) for x in range(0, dir.count(os.sep))]:
    if root in PLEX_LIBRARY:
      library = PLEX_LIBRARY[root]
      path    = os.path.relpath(dir, root)
      break
  else:  #401 no right to list libraries (windows)
    Log.Info(u'[!] Library access denied')
    filename = os.path.join(CachePath, '_Logs', '_root_.scanner.log')
    if os.path.isfile(filename):
      Log.Info(u'[!] ASS root scanner file present: "{}"'.format(filename))
      line = Core.storage.load(filename)  #with open(filename, 'rb') as file:  line=file.read()
      for root in [os.sep.join(dir.split(os.sep)[0:x+2]) for x in range(dir.count(os.sep)-1, -1, -1)]:
        if "root: '{}'".format(root) in line:  path = os.path.relpath(dir, root).rstrip('.');  break  #Log.Info(u'[!] root not found: "{}"'.format(root))
      else: path, root = '_unknown_folder', ''
    else:  Log.Info(u'[!] ASS root scanner file missing: "{}"'.format(filename))
  return library, root, path


#> called when looking for encora API Key
def encora_api_key():
  path = os.path.join(PluginDir, "encora-key.txt")
  if os.path.isfile(path):
    value = Data.Load(path)
    if value:
      value = value.strip()
    if value:
      Log.Debug(u"Loaded token from encora-token.txt file")

      return value

  # Fall back to Library preference
  return Prefs['encora_api_key']


###
def json_load(template, *args):
  url = template.format(*args + tuple([encora_api_key()]))
  url = sanitize_path(url)
  iteration = 0
  json_page = {}
  json      = {}
  while not json or Dict(json_page, 'nextPageToken') and Dict(json_page, 'pageInfo', 'resultsPerPage') !=1 and iteration<50:
    #Log.Info(u'{}'.format(Dict(json_page, 'pageInfo', 'resultsPerPage')))
    try:                    json_page = JSON.ObjectFromURL(url+'&pageToken='+Dict(json_page, 'nextPageToken') if Dict(json_page, 'nextPageToken') else url)  #Log.Info(u'items: {}'.format(len(Dict(json_page, 'items'))))
    except Exception as e:  json = JSON.ObjectFromString(e.content);  raise ValueError('code: {}, message: {}'.format(Dict(json, 'error', 'code'), Dict(json, 'error', 'message')))
    if json:  json ['items'].extend(json_page['items'])
    else:     json = json_page
    iteration +=1
  #Log.Info(u'total items: {}'.format(len(Dict(json, 'items'))))
  return json

def Start():
  HTTP.CacheTime                  = CACHE_1MONTH
  HTTP.Headers['User-Agent'     ] = 'Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.54'
  HTTP.Headers['Accept-Language'] = 'en-us'

### Assign unique ID ###
def Search(results, media, lang, manual, movie):
    displayname = sanitize_path(os.path.basename((media.name if movie else media.show) or ""))
    filename = media.items[0].parts[0].file if movie else media.filename or media.show
    dir = GetMediaDir(media, movie)
    
    try:
        filename = sanitize_path(filename)
    except Exception as e:
        Log('search() - Exception1: filename: "{}", e: "{}"'.format(filename, e))
    try:
        filename = os.path.basename(filename)
    except Exception as e:
        Log('search() - Exception2: filename: "{}", e: "{}"'.format(filename, e))
    try:
        filename = urllib2.unquote(filename)
    except Exception as e:
        Log('search() - Exception3: filename: "{}", e: "{}"'.format(filename, e))
    
    Log(u''.ljust(157, '='))
    Log(u"Search() - dir: {}, filename: {}, displayname: {}".format(dir, filename, displayname))
    
    # Extract recording ID from the folder name
    folder_name = os.path.basename(dir)
    recording_id_match = re.search(r'e-(\d+)', folder_name)
    
    if recording_id_match:
        recording_id = recording_id_match.group(1)
        Log(u'search() - Found recording ID: {}'.format(recording_id))
        
        try:
            json_recording_details = json_load(ENCORA_API_RECORDING_INFO, recording_id)
            if json_recording_details:
                Log.Info(u'filename: "{}", title: "{}"'.format(filename, json_recording_details['show']))
                results.Append(MetadataSearchResult(
                    id='encora|{}|{}'.format(recording_id, os.path.basename(dir)),
                    name=json_recording_details['show'],
                    year=Datetime.ParseDate(json_recording_details['date']['full_date']).year,
                    score=100,
                    lang=lang
                ))
                Log(u''.ljust(157, '='))
                return
        except Exception as e:
            Log(u'search() - Could not retrieve data from Encora API for: "{}", Exception: "{}"'.format(recording_id, e))
    
    # If no recording ID is found, log and return a default result
    Log(u'search() - No recording ID found in folder name: "{}"'.format(folder_name))
    library, root, path = GetLibraryRootPath(dir)
    Log(u'Putting folder name "{}" as guid since no assigned recording ID was found'.format(path.split(os.sep)[-1]))
    results.Append(MetadataSearchResult(
        id='encora|{}|{}'.format(path.split(os.sep)[-2] if os.sep in path else '', dir),
        name=os.path.basename(filename),
        year=None,
        score=80,
        lang=lang
    ))
    Log(''.ljust(157, '='))

### Download metadata using encora ID ###
def Update(metadata, media, lang, force, movie):
    Log(u'=== update(lang={}, force={}, movie={}) ==='.format(lang, force, movie))
    temp1, recording_id, series_folder = metadata.id.split("|")
    dir = sanitize_path(GetMediaDir(media, movie))
    series_folder = sanitize_path(series_folder)
    Log(u''.ljust(157, '='))

    try:
        json_recording_details = json_load(ENCORA_API_RECORDING_INFO, recording_id)
        if json_recording_details:
            # Update metadata fields based on the Encora API response
            metadata.title = json_recording_details['show']
            metadata.sort_title = json_recording_details['show']
            metadata.original_title = json_recording_details['show']
            metadata.originally_available_at = Datetime.ParseDate(json_recording_details['date']['full_date']).date()
            metadata.studio = json_recording_details['tour']
            metadata.directors.clear()
            director = metadata.directors.new()
            director.name = json_recording_details['master']

            # Set content rating based on NFT status
            nft_date = json_recording_details['nft']['nft_date']
            nft_forever = json_recording_details['nft']['nft_forever']
            if nft_forever or (nft_date and Datetime.ParseDate(nft_date) < Datetime.Now()):
                metadata.content_rating = 'NFT'

            # Update genres based on recording type
            metadata.genres.clear()
            recording_type = json_recording_details['metadata']['recording_type']
            if recording_type:
                metadata.genres.add(recording_type)
            if json_recording_details['metadata']['media_type']:
                metadata.genres.add(json_recording_details['metadata']['media_type'])

            # Set cast and crew
            metadata.roles.clear()
            for cast_member in json_recording_details['cast']:
                role = metadata.roles.new()
                role.actor = cast_member['performer']['name']
                role.role = cast_member['character']['name']
                role.photo = cast_member['performer']['url']  # Assuming the URL can be used as a photo

            # Log the updated metadata
            Log(u'Updated metadata: title="{}", sort_title="{}", original_title="{}", originally_available_at="{}", studio="{}", director="{}", content_rating="{}", genres="{}", roles="{}"'.format(
                metadata.title, metadata.sort_title, metadata.original_title, metadata.originally_available_at, metadata.studio, director.name, metadata.content_rating, list(metadata.genres), [(role.actor, role.role) for role in metadata.roles]
            ))

            return
    except Exception as e:
        Log(u'update() - Could not retrieve data from Encora API for: "{}", Exception: "{}"'.format(recording_id, e))

    Log('=== End Of Agent Call, errors after that are Plex related ==='.ljust(157, '='))

    ### Movie - API call ################################################################################################################
    Log(u'update() using api - guid: {}, dir: {}, metadata.id: {}'.format(guid, dir, metadata.id))
    try:
        json_recording_details = json_load(ENCORA_API_RECORDING_INFO, guid)
    except Exception as e:
        Log(u'json_recording_details - Could not retrieve data from Encora API for: {}, Exception: {}'.format(guid, e))
    else:
        Log('Movie mode - json_recording_details - Loaded recording details from: "{}"'.format(ENCORA_API_RECORDING_INFO.format(guid, 'personal_key')))
        date = Datetime.ParseDate(json_recording_details['date']['full_date'])
        Log('date:  "{}"'.format(date))
        metadata.originally_available_at = date.date()
        metadata.title = json_recording_details['show']
        Log(u'series title:       "{}"'.format(json_recording_details['show']))
        metadata.summary = json_recording_details['notes']
        Log(u'series description: {}'.format(json_recording_details['notes'].replace('\n', '. ')))
        metadata.genres.clear()
        recording_type = json_recording_details['metadata']['recording_type']
        if recording_type:
            metadata.genres.add(recording_type)
        if json_recording_details['metadata']['media_type']:
            metadata.genres.add(json_recording_details['metadata']['media_type'])
        Log(u'genres: {}'.format([x for x in metadata.genres]))
        metadata.year = date.year
        Log(u'movie year: {}'.format(date.year))
        
        # Set content rating based on NFT status
        nft_date = json_recording_details['nft']['nft_date']
        nft_forever = json_recording_details['nft']['nft_forever']
        if nft_forever or (nft_date and Datetime.ParseDate(nft_date) < Datetime.Now()):
            metadata.content_rating = 'NFT'
        
        # Set cast and crew
        metadata.roles.clear()
        for cast_member in json_recording_details['cast']:
            role = metadata.roles.new()
            role.actor = cast_member['performer']['name']
            role.role = cast_member['character']['name']
            #role.photo = cast_member['performer']['url'] # this needs to query new headshot database
        
        if Prefs['add_user_as_director']:
            metadata.directors.clear()
            try:
                meta_director = metadata.directors.new()
                meta_director.name = json_recording_details['master']
                Log(u'director: {}'.format(json_recording_details['master']))
            except Exception as e:
                Log.Info(u'[!] add_user_as_director exception: {}'.format(e))
        return
    
    Log('=== End Of Agent Call, errors after that are Plex related ==='.ljust(157, '='))

### Agent declaration ##################################################################################################################################################
class EncoraAgent(Agent.Movies):
  name, primary_provider, fallback_agent, contributes_to, accepts_from, languages = 'Encora', True, None, None, ['com.plexapp.agents.localmedia'], [Locale.Language.NoLanguage]
  def search (self, results,  media, lang, manual):  Search (results,  media, lang, manual, True)
  def update (self, metadata, media, lang, force ):  Update (metadata, media, lang, force,  True)

### Variables ###
PluginDir                = os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), "..", ".."))
PlexRoot                 = os.path.abspath(os.path.join(PluginDir, "..", ".."))
CachePath                = os.path.join(PlexRoot, "Plug-in Support", "Data", "com.plexapp.agents.hama", "DataItems")
PLEX_LIBRARY             = {}
PLEX_LIBRARY_URL         = "http://127.0.0.1:32400/library/sections/"    # Allow to get the library name to get a log per library https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token
ENCORA_API_BASE_URL      = "https://encora.it/api/"
ENCORA_API_RECORDING_INFO= ENCORA_API_BASE_URL + 'recording/{}' # fetch recording data

# YOUTUBE_CHANNEL_DETAILS  = ENCORA_API_BASE_URL + 'channels?part=snippet%2CcontentDetails%2Cstatistics%2CbrandingSettings&id={}&key={}'
# YOUTUBE_CHANNEL_REGEX    = Regex('\[(?:youtube(|2)\-)?(?P<id>UC[a-zA-Z0-9\-_]{22}|HC[a-zA-Z0-9\-_]{22})\]')
# YOUTUBE_PLAYLIST_ITEMS   = ENCORA_API_BASE_URL + 'playlistItems?part=snippet,contentDetails&maxResults=50&playlistId={}&key={}'
# YOUTUBE_PLAYLIST_DETAILS = ENCORA_API_BASE_URL + 'playlists?part=snippet,contentDetails&id={}&key={}'
# YOUTUBE_PLAYLIST_REGEX   = Regex('\[(?:youtube(|3)\-)?(?P<id>PL[^\[\]]{16}|PL[^\[\]]{32}|UU[^\[\]]{22}|FL[^\[\]]{22}|LP[^\[\]]{22}|RD[^\[\]]{22}|UC[^\[\]]{22}|HC[^\[\]]{22})\]',  Regex.IGNORECASE)  # https://regex101.com/r/37x8wI/2
# YOUTUBE_VIDEO_SEARCH     = ENCORA_API_BASE_URL + 'search?&maxResults=1&part=snippet&q={}&key={}'
# YOUTUBE_json_video_details    = ENCORA_API_BASE_URL + 'videos?part=snippet,contentDetails,statistics&id={}&key={}'
# YOUTUBE_VIDEO_REGEX      = Regex('(?:^\d{8}_|\[(?:youtube\-)?)(?P<id>[a-z0-9\-_]{11})(?:\]|_)', Regex.IGNORECASE) # https://regex101.com/r/zlHKPD/1
# YOUTUBE_CATEGORY_ID      = {  '1': 'Film & Animation',  '2': 'Autos & Vehicles',  '10': 'Music',          '15': 'Pets & Animals',        '17': 'Sports',                 '18': 'Short Movies',
#                              '19': 'Travel & Events',  '20': 'Gaming',            '21': 'Videoblogging',  '22': 'People & Blogs',        '23': 'Comedy',                 '24': 'Entertainment',
#                              '25': 'News & Politics',  '26': 'Howto & Style',     '27': 'Education',      '28': 'Science & Technology',  '29': 'Nonprofits & Activism',  '30': 'Movies',
#                              '31': 'Anime/Animation',  '32': 'Action/Adventure',  '33': 'Classics',       '34': 'Comedy',                '35': 'Documentary',            '36': 'Drama', 
#                              '37': 'Family',           '38': 'Foreign',           '39': 'Horror',         '40': 'Sci-Fi/Fantasy',        '41': 'Thriller',               '42': 'Shorts',
#                              '43': 'Shows',            '44': 'Trailers'}
### Plex Library XML ###
Log.Info(u"Library: "+PlexRoot)  #Log.Info(file)
token_file_path = os.path.join(PlexRoot, "X-Plex-Token.id")
if os.path.isfile(token_file_path):
  Log.Info(u"'X-Plex-Token.id' file present")
  token_file=Data.Load(token_file_path)
  if token_file:  PLEX_LIBRARY_URL += "?X-Plex-Token=" + token_file.strip()
try:
  library_xml = etree.fromstring(urllib2.urlopen(PLEX_LIBRARY_URL).read())
  for library in library_xml.iterchildren('Directory'):
    for path in library.iterchildren('Location'):
      PLEX_LIBRARY[path.get("path")] = library.get("title")
      Log.Info(u"{} = {}".format(path.get("path"), library.get("title")))
except Exception as e:  Log.Info(u"Place correct Plex token in {} file or in PLEX_LIBRARY_URL variable in Code/__init__.py to have a log per library - https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token, Error: {}".format(token_file_path, str(e)))
