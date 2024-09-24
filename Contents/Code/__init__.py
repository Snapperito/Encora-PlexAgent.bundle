# -*- coding: utf-8 -*-

### Imports ###
import sys                  # getdefaultencoding, getfilesystemencoding, platform, argv
import os                   # path.abspath, join, dirname
import re                   #
import inspect              # getfile, currentframe
import urllib2
import urllib
from   lxml    import etree #
from   io      import open  # open
import hashlib
from datetime import datetime
import time
import json

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

# Function to parse ISO 8601 date string and handle 'Z' for UTC
def parse_iso8601(nft_date):
    if nft_date.endswith('Z'):
        nft_date = nft_date[:-1]  # Remove the 'Z'
        return datetime.strptime(nft_date, '%Y-%m-%dT%H:%M:%S.%f')  # Parse the datetime string
    return None  # Return None if the format is unexpected

def download_subtitles(recording_id, media, movie):
    subtitles_url = "https://encora.it/api/recording/{}/subtitles".format(recording_id)
    headers = {
        'Authorization': 'Bearer {}'.format(encora_api_key()),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    try:
        request = urllib2.Request(subtitles_url, headers=headers)
        response = urllib2.urlopen(request)
        json_data = json.load(response)

        if json_data and isinstance(json_data, list) and len(json_data) > 0:
            subtitle_info = json_data[0]
            subtitle_file_url = subtitle_info['url']
            file_type = subtitle_info['file_type']
            subtitle_file_path = os.path.join(GetMediaDir(media, True), "{}.{}".format(media.title, file_type))

            #Log sub file path
            Log.Info("Subtitle file path: {}".format(subtitle_file_path))

            filename = media.items[0].parts[0].file if movie else media.filename or media.show
            dir = GetMediaDir(media, movie)
            
            try:
                filename = sanitize_path(filename)
            except Exception as e:
                Log('download_subtitles() - Exception1: filename: "{}", e: "{}"'.format(filename, e))
            try:
                filename = os.path.basename(filename)
            except Exception as e:
                Log('download_subtitles() - Exception2: filename: "{}", e: "{}"'.format(filename, e))
            try:
                filename = urllib2.unquote(filename)
            except Exception as e:
                Log('download_subtitles() - Exception3: filename: "{}", e: "{}"'.format(filename, e))
            
            Log(u''.ljust(157, '='))

            # Replace the title after the last \ with filename and convert .ext to lowercase
            # filename without ext
            filename_without_ext = os.path.splitext(filename)[0]
            subtitle_file_path = os.path.join(dir, "{}.{}".format(filename_without_ext, file_type.lower()))

            # Download the subtitle file
            request = urllib2.Request(subtitle_file_url, headers=headers)

            # Open the URL and write the content to the file
            with open(subtitle_file_path, 'wb') as f:
                f.write(urllib2.urlopen(request).read())
            Log.Info("Downloaded subtitles to: {}".format(subtitle_file_path))

            # Attach downloaded subtitle to media metadata
            mediaPart = media.items[0].parts[0]
            content = open(subtitle_file_path, 'r').read()

            pm = Proxy.Media(content, ext=file_type, forced="1" if subtitle_info.get('forced') else None)
            new_key = "subzero_md" + ("_forced" if subtitle_info.get('forced') else "")
            lang = Locale.Language.Match(subtitle_info.get('language'))

            # Remove any legacy subtitles and add the new one
            for key, proxy in getattr(mediaPart.subtitles[lang], "_proxies").iteritems():
                if not proxy or not len(proxy) >= 5:
                    Log.Debug("Can't parse metadata: %s" % repr(proxy))
                    continue
            Log.Debug("Adding metadata sub for %s: %s", lang, subtitle_file_path)
            mediaPart.subtitles[lang][new_key] = pm
        else:
            Log.Info("No subtitle file found for recording ID: {}".format(recording_id))

    except Exception as e:
        Log.Error("Failed to download subtitles for recording ID: {}: {}".format(recording_id, str(e)))


    except Exception as e:
        Log.Error("Failed to download subtitles for recording ID: {}: {}".format(recording_id, str(e)))



# Used for the preference to define the format of Plex Titles
def format_title(template, data):    
    date_info = data.get('date', {})
    full_date = ""
    
    if date_info.get('day_known') is False:
        if date_info.get('month_known') is False:
            full_date = date_info.get('full_date')[:4]  # Return YYYY
        else:
            full_date = "{}, {}".format(month_name(date_info.get('month', 1)), date_info.get('full_date')[:4])  # Return Month, YYYY
    else:
        full_date = date_info.get('full_date', '').lower()
        date_variant = date_info.get('date_variant')
        if date_variant:
            full_date += " ({})".format(date_variant)

    title = template
    title = title.replace('{show}', data.get('show', ''))
    title = title.replace('{tour}', data.get('tour', ''))
    title = title.replace('{date}', full_date)
    title = title.replace('{master}', data.get('master', ''))

    Log.Info(u'output title: "{}"'.format(title))
    return title

def month_name(month):
    # Return the full name of the month
    return [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ][month]

def clean_html_description(html_description):
    # Preserve line breaks
    text = re.sub(r'</p>', '\n', html_description)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Manually replace common HTML entities
    text = text.replace('&#039;', "'")
    text = text.replace('&quot;', '"')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    return text

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
    url = template.format(*args)
    url = sanitize_path(url)
    iteration = 0
    json_page = {}
    json_data = {}

    # Bearer token
    headers = {
        'Authorization': 'Bearer {}'.format(encora_api_key())  # Use the bearer token
    }

    while not json_data or Dict(json_page, 'nextPageToken') and Dict(json_page, 'pageInfo', 'resultsPerPage') != 1 and iteration < 50:
        try:
            full_url = url + '&pageToken=' + Dict(json_page, 'nextPageToken') if Dict(json_page, 'nextPageToken') else url
            json_page = JSON.ObjectFromURL(full_url, headers=headers)  # Pass headers to the request
        except Exception as e:
            json_data = JSON.ObjectFromString(e.content)
            raise ValueError('code: {}, message: {}'.format(Dict(json_data, 'error', 'code'), Dict(json_data, 'error', 'message')))
        
        if json_data:
            json_data['items'].extend(json_page['items'])
        else:
            json_data = json_page
        
        iteration += 1

    return json_data

def find_encora_id_file(directory):
    pattern = re.compile(r'\.encora-(\d+)')
    
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            return match.group(1)
    
    # If no match found, check for .encora-id file
    encora_id_file = os.path.join(directory, '.encora-id')
    if os.path.isfile(encora_id_file):
        with open(encora_id_file, 'r') as file:
            return file.read().strip()
    
    return None
    
def Start():
  #HTTP.CacheTime                  = CACHE_1DAY
  HTTP.Headers['User-Agent'     ] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
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
    # Try to find the recording ID from folder name
    recording_id_match = re.search(r'e-(\d+)', dir)
    if recording_id_match:
        recording_id = recording_id_match.group(1)
        Log(u'search() - Found recording ID in folder name: {}'.format(recording_id))
    else:
        # Fallback to checking for .encora_{id} file inside the folder

        recording_id = find_encora_id_file(dir)
        if recording_id:
            Log(u'search() - Found recording ID in filename: {}'.format(recording_id))
        else:
            Log(u'search() - No recording ID found in filenames')
    if recording_id:
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
            #log "downloading subtitles"
            Log(u'Attempting to download subtitles for recording ID: {}'.format(recording_id))
            download_subtitles(recording_id, media, movie)
            # Update metadata fields based on the Encora API response
            metadata.title = format_title(Prefs['title_format'], json_recording_details)
            metadata.original_title = json_recording_details['show']
            metadata.originally_available_at = Datetime.ParseDate(json_recording_details['date']['full_date']).date()
            metadata.studio = json_recording_details['tour']
            metadata.directors.clear()
            director = metadata.directors.new()
            director.name = json_recording_details['master']
            show_description_html = json_recording_details.get('metadata', {}).get('show_description', 'Not provided. Edit the show on Encora to populate this!')
            show_description = clean_html_description(show_description_html)
            metadata.summary = show_description


            # Set content rating based on NFT status
            nft_date = json_recording_details['nft']['nft_date']
            nft_forever = json_recording_details['nft']['nft_forever']

            # Parse the nft_date in ISO 8601 format
            if nft_date:
                nft_date_parsed = parse_iso8601(nft_date)
            else:
                nft_date_parsed = None

            # Get the current time in UTC (naive datetime)
            current_time = datetime.utcnow()

            # Compare only when nft_date is present and properly parsed
            if nft_forever or (nft_date_parsed and nft_date_parsed < current_time):
                metadata.content_rating = 'NFT'

            # Create a cast array
            cast_array = json_recording_details['cast']
            show_id = json_recording_details['metadata']['show_id']

            # Prepare media db api query
            media_db_api_url = "https://website.com/api/media?show_id={}&performers=[{}]".format(show_id, ','.join([str(x['performer']['id']) for x in cast_array]))
            Log(u'media_db_api_url: {}'.format(media_db_api_url))

            # Update genres based on recording type
            metadata.genres.clear()
            recording_type = json_recording_details['metadata']['recording_type']
            if recording_type:
                metadata.genres.add(recording_type)
            if json_recording_details['metadata']['media_type']:
                metadata.genres.add(json_recording_details['metadata']['media_type'])

            metadata.roles.clear()
            for cast_member in json_recording_details['cast']:
                role = metadata.roles.new()
                role.name = cast_member['performer']['name'] # Performer name = role.name
                if cast_member['status']:
                    role.role = cast_member['status']['abbreviation'].lower() + ' ' + cast_member['character']['name'] # Character status + name = role.role
                else:
                    role.role = cast_member['character']['name'] # Character name = role.role
                #role.photo = cast_member['performer']['url'] # this needs to query new headshot database
            if Prefs['add_master_as_director']:
                metadata.directors.clear()
                try:
                    meta_director = metadata.directors.new()
                    meta_director.name = json_recording_details['master']
                    Log(u'director: {}'.format(json_recording_details['master']))
                except Exception as e:
                    Log.Info(u'[!] add_master_as_director exception: {}'.format(e))
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
        format_title(Prefs['title_format'], json_recording_details)
        show_description_html = json_recording_details.get('metadata', {}).get('show_description', 'Not provided. Edit the show on Encora to populate this!')
        show_description = clean_html_description(show_description_html)
        metadata.summary = show_description
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

        # Parse the nft_date in ISO 8601 format
        if nft_date:
            nft_date_parsed = parse_iso8601(nft_date)
        else:
            nft_date_parsed = None

        # Get the current time in UTC (naive datetime)
        current_time = datetime.utcnow()

        # Compare only when nft_date is present and properly parsed
        if nft_forever or (nft_date_parsed and nft_date_parsed < current_time):
            metadata.content_rating = 'NFT'
        
        metadata.roles.clear()
        for cast_member in json_recording_details['cast']:
            role = metadata.roles.new()
            role.name = cast_member['performer']['name'] # Performer name = role.name
            if cast_member['status']:
                role.role = cast_member['status']['abbreviation'].lower() + ' ' + cast_member['character']['name'] # Character status + name = role.role
            else:
                role.role = cast_member['character']['name'] # Character name = role.role
            #role.photo = cast_member['performer']['url'] # this needs to query new headshot database
            Log(u'Found Cast Member: actor: {}, role: {}'.format(role.name, role.role))
        if Prefs['add_master_as_director']:
            metadata.directors.clear()
            try:
                meta_director = metadata.directors.new()
                meta_director.name = json_recording_details['master']
                Log(u'director: {}'.format(json_recording_details['master']))
            except Exception as e:
                Log.Info(u'[!] add_master_as_director exception: {}'.format(e))
        return
    
    Log('=== End Of Agent Call, errors after that are Plex related ==='.ljust(157, '='))

### Agent declaration ##################################################################################################################################################
class EncoraAgent(Agent.Movies):
  name, primary_provider, fallback_agent, contributes_to, accepts_from, languages = 'Encora', True, ['com.plexapp.agents.xbmcnfo'], None, ['com.plexapp.agents.localmedia', 'com.plexapp.agents.xbmcnfo'], [Locale.Language.NoLanguage]
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
