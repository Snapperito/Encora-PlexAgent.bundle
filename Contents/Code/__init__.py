# -*- coding: utf-8 -*-

### Imports ###
import sys                  # getdefaultencoding, getfilesystemencoding, platform, argv
import os                   # path.abspath, join, dirname
import re                   #
import inspect
import urllib2
import urllib
from   lxml    import etree #
from   io      import open  # open
import hashlib
from datetime import datetime, timedelta
import time
import json
import requests
import traceback

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
        'User-Agent': 'PlexAgent/0.9'
    }

    try:
        request = urllib2.Request(subtitles_url, headers=headers)
        response = urllib2.urlopen(request)
        json_data = json.load(response)

        if json_data and isinstance(json_data, list) and len(json_data) > 0:
            mediaPart = media.items[0].parts[0]

            # Loop over all subtitle entries
            for subtitle_info in json_data:
                subtitle_file_url = subtitle_info['url']
                file_type = subtitle_info['file_type']
                language = subtitle_info['language']
                forced = subtitle_info.get('forced')

                filename = media.items[0].parts[0].file if movie else media.filename or media.show
                dir = GetMediaDir(media, movie)

                try:
                    filename = sanitize_path(filename)
                except Exception as e:
                    Log('[Encora] download_subtitles() - Exception1: filename: "{}", e: "{}"'.format(filename, e))
                try:
                    filename = os.path.basename(filename)
                except Exception as e:
                    Log('[Encora] download_subtitles() - Exception2: filename: "{}", e: "{}"'.format(filename, e))
                try:
                    filename = urllib2.unquote(filename)
                except Exception as e:
                    Log('[Encora] download_subtitles() - Exception3: filename: "{}", e: "{}"'.format(filename, e))

                filename_without_ext = os.path.splitext(filename)[0]
                subtitle_file_path = os.path.join(dir, "{}_{}.{}".format(filename_without_ext, language, file_type.lower()))

                # Download the subtitle file
                subtitle_request = urllib2.Request(subtitle_file_url, headers=headers)

                # Write the content to the file
                with open(subtitle_file_path, 'wb') as f:
                    f.write(urllib2.urlopen(subtitle_request).read())
                Log.Info("[Encora] Downloaded subtitles to: {}".format(subtitle_file_path))

                # Attach downloaded subtitle to media metadata
                with open(subtitle_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                pm = Proxy.Media(content, ext=file_type, forced="1" if forced else None)
                new_key = "subzero_md" + ("_forced" if forced else "")
                lang = Locale.Language.Match(language)

                # Remove any legacy subtitles for the same language and add the new one
                mediaPart.subtitles[lang][new_key] = pm
                Log.Debug("[Encora] Added subtitle for language '{}': {}".format(language, subtitle_file_path))

    except Exception as e:
        Log.Error("[Encora] Failed to download subtitles for recording ID: {}: {}".format(recording_id, str(e)))

def format_date(data):
    replace_char = Prefs['date_replace_char']
    if (len(replace_char) > 1): 
        replace_char = replace_char[0]
    replace_char = replace_char * 2
    date_info = data.get('date', {})
    full_date = ""
    iso_date = ""
    usa_date = ""
    numeric_date = ""
    
    if date_info.get('day_known') is False:
        if date_info.get('month_known') is False:
            full_date = date_info.get('full_date')[:4]  # Return YYYY
            iso_date = "{}-{}-{}".format(date_info.get('full_date')[:4], replace_char, replace_char)  # Return YYYY-xx-xx
            usa_date = "{}-{}-{}".format(replace_char, replace_char, date_info.get('full_date')[:4])  # Return xx-xx-YYYY
            numeric_date = "{}-{}-{}".format(replace_char, replace_char, date_info.get('full_date')[:4])  # Return xx-xx-YYYY
        else:
            month = date_info.get('full_date')[5:7]
            full_date = "{}, {}".format(month_name(int(month)), date_info.get('full_date')[:4])  # Return Month, YYYY
            iso_date = "{}-{}-{}".format(date_info.get('full_date')[:4], month, replace_char)  # Return YYYY-MM-xx
            usa_date = "{}-{}-{}".format(month, replace_char, date_info.get('full_date')[:4])  # Return MM-xx-YYYY
            numeric_date = "{}-{}-{}".format(replace_char, month, date_info.get('full_date')[:4])  # Return xx-MM-YYYY
    else:
        try:
            full_date = datetime.strptime(date_info.get('full_date'), "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")
            iso_date = date_info.get('full_date')
            usa_date = datetime.strptime(date_info.get('full_date'), "%Y-%m-%d").strftime("%m-%d-%Y")
            numeric_date = datetime.strptime(date_info.get('full_date'), "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError as e:
            Log(u'[Encora] Date format error: {}'.format(e))
        except Exception as e:
            Log(u'[Encora] An unexpected error occurred: {}'.format(e))
    
    date_variant = date_info.get('date_variant')
    variant = " ({})".format(date_variant) if date_variant else ""    

    return {
        'full_date': full_date + variant,
        'iso': iso_date + variant,
        'usa': usa_date + variant,
        'numeric': numeric_date + variant
    }

# Used for the preference to define the format of Plex Titles
def format_title(template, data):    
    date = format_date(data)
    title = template
    title = title.replace('{show}', data.get('show', ''))
    title = title.replace('{tour}', data.get('tour', ''))
    title = title.replace('{date}', date['full_date'])
    title = title.replace('{date_iso}', date['iso'])
    title = title.replace('{date_usa}', date['usa'])
    title = title.replace('{date_numeric}', date['numeric'])
    title = title.replace('{master}', data.get('master', ''))
    title = title.replace(' - Part One', '')
    title = title.replace(' - Part 1', '')
    title = title.replace(' - Part I', '')
    title = title.replace(' - Part Two', '')
    title = title.replace(' - Part 2', '')
    title = title.replace(' - Part II', '')
    return title

def month_name(month):
    # Return the full name of the month
    return [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ][month]

def clean_html_description(html_description):
    if html_description:
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
    else:
        return ''

### Get media root folder ###
def GetLibraryRootPath(dir):
  library, root, path = '', '', ''
  for root in [os.sep.join(dir.split(os.sep)[0:x+2]) for x in range(0, dir.count(os.sep))]:
    if root in PLEX_LIBRARY:
      library = PLEX_LIBRARY[root]
      path    = os.path.relpath(dir, root)
      break
  else:  #401 no right to list libraries (windows)
    Log.Info(u'[Encora]  Library access denied')
    filename = os.path.join(CachePath, '_Logs', '_root_.scanner.log')
    if os.path.isfile(filename):
      Log.Info(u'[Encora]  ASS root scanner file present: "{}"'.format(filename))
      line = Core.storage.load(filename)  #with open(filename, 'rb') as file:  line=file.read()
      for root in [os.sep.join(dir.split(os.sep)[0:x+2]) for x in range(dir.count(os.sep)-1, -1, -1)]:
        if "root: '{}'".format(root) in line:  path = os.path.relpath(dir, root).rstrip('.');  break  #Log.Info(u'[!] root not found: "{}"'.format(root))
      else: path, root = '_unknown_folder', ''
    else:  Log.Info(u'[Encora]  ASS root scanner file missing: "{}"'.format(filename))
  return library, root, path


#> called when looking for encora API Key
def encora_api_key():
  path = os.path.join(PluginDir, "encora-key.txt")
  if os.path.isfile(path):
    value = Data.Load(path)
    if value:
      value = value.strip()
    if value:
      Log.Debug(u"[Encora] Loaded token from encora-token.txt file")

      return value

  # Fall back to Library preference
  return Prefs['encora_api_key']

#> called when looking for stagemedia API Key
def stagemedia_api_key():
  path = os.path.join(PluginDir, "stagemedia-key.txt")
  if os.path.isfile(path):
    value = Data.Load(path)
    if value:
      value = value.strip()
    if value:
      Log.Debug(u"[Encora] Loaded token from stagemedia-token.txt file")

      return value

  # Fall back to Library preference
  return Prefs['stagemedia_api_key']

def make_request(url, headers={}):
    # Initialize variables
    response = None
    str_error = None

    sleep_time = 1
    num_retries = 4
    for x in range(0, num_retries):
        Log('[Encora] Requesting: {}'.format(url))
        try:
            response = requests.get(url, headers=headers, timeout=90, verify=False)
        except Exception as str_error:
            Log('[Encora] Failed HTTP request: {} | {}'.format(x, url))
            Log('[Encora] {}'.format(str_error))

        if str_error:
            time.sleep(sleep_time)
            sleep_time = sleep_time * x
        else:
            break

    return response.content if response else response

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
  HTTP.Headers['User-Agent'     ] = 'PlexAgent/0.9'
  HTTP.Headers['Accept-Language'] = 'en-us'

### Assign unique ID ###
def Search(results, media, lang, manual, movie):
    displayname = sanitize_path(os.path.basename((media.name if movie else media.show) or ""))
    filename = media.items[0].parts[0].file if movie else media.filename or media.show
    dir = GetMediaDir(media, movie)
    
    try:
        filename = sanitize_path(filename)
    except Exception as e:
        Log('[Encora] search() - Exception1: filename: "{}", e: "{}"'.format(filename, e))
    try:
        filename = os.path.basename(filename)
    except Exception as e:
        Log('[Encora] search() - Exception2: filename: "{}", e: "{}"'.format(filename, e))
    try:
        filename = urllib2.unquote(filename)
    except Exception as e:
        Log('[Encora] search() - Exception3: filename: "{}", e: "{}"'.format(filename, e))
    
    Log(u''.ljust(157, '='))
    Log(u"[Encora] Search() - dir: {}, filename: {}, displayname: {}".format(dir, filename, displayname))
    
    # Extract recording ID from the folder name
    folder_name = os.path.basename(dir)
    # Try to find the recording ID from folder name
    recording_id_match = re.search(r'e-(\d+)', dir)
    if recording_id_match:
        recording_id = recording_id_match.group(1)
        Log(u'[Encora] search() - Found recording ID in folder name: {}'.format(recording_id))
    else:
        # Fallback to checking for .encora_{id} file inside the folder

        recording_id = find_encora_id_file(dir)
        if recording_id:
            Log(u'[Encora] search() - Found recording ID in filename: {}'.format(recording_id))
        else:
            Log(u'[Encora] search() - No recording ID found in filenames')
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
            tb = traceback.format_exc()
            Log(u'[Encora] update() - Could not retrieve data from Encora API for: "{}", Exception: "{}"'.format(recording_id, e))
            Log(u'[Encora] update() - Traceback: {}'.format(tb))
    
    # If no recording ID is found, log and return a default result
    Log(u'[Encora] search() - No recording ID found in folder name: "{}"'.format(folder_name))
    library, root, path = GetLibraryRootPath(dir)
    Log(u'[Encora] Putting folder name "{}" as guid since no assigned recording ID was found'.format(path.split(os.sep)[-1]))
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
            try:
                Log(u'[Encora] Attempting to download subtitles for recording ID: {}'.format(recording_id))
                download_subtitles(recording_id, media, movie)
            except Exception as e:
                # Handle the exception (e.g., log the error, retry, etc.)
                Log(u"[Encora] An error occurred while downloading subtitles: {}".format(e))
            Log(u'[Encora] Setting metadata for recording ID: {}'.format(recording_id))
            # Update metadata fields based on the Encora API response
            metadata.title = format_title(Prefs['title_format'], json_recording_details)
            Log(u'[Encora] title: {}'.format(metadata.title))
            metadata.original_title = json_recording_details['show']
            Log(u'[Encora] original_title: {}'.format(metadata.original_title))
            metadata.originally_available_at = (datetime.strptime(json_recording_details['date']['full_date'], "%Y-%m-%d") + timedelta(days=1)).date()
            Log(u'[Encora] originally_available_at: {}'.format(metadata.originally_available_at))
            metadata.studio = json_recording_details['tour']
            Log(u'[Encora] studio: {}'.format(metadata.studio))
            metadata.directors.clear()
            director = metadata.directors.new()
            director.name = json_recording_details['master']
            Log(u'[Encora] director: {}'.format(director.name))
            show_description_html = json_recording_details.get('metadata', {}).get('show_description', 'Not provided. Edit the show on Encora to populate this!')
            show_description = clean_html_description(show_description_html)
            metadata.summary = show_description
            Log(u'[Encora] show_description_html: {}'.format(clean_html_description(show_description_html)))
            #log updated metadata
            Log(u'[Encora] Updated metadata for recording ID: {}'.format(recording_id))

            if (Prefs['create_show_collections']): 
                collection = metadata.collections.add(json_recording_details["show"])

            # Set content rating based on NFT status
            nft_date = json_recording_details['nft']['nft_date']
            nft_forever = json_recording_details['nft']['nft_forever']

            # Parse the nft_date in ISO 8601 format
            nft_date_parsed = parse_iso8601(nft_date) if nft_date else None

            # Get the current time in UTC (naive datetime)
            current_time = datetime.utcnow()

            # Compare only when nft_date is present and properly parsed
            if nft_forever or (nft_date_parsed and nft_date_parsed > current_time):
                metadata.content_rating = 'NFT'
            else:
                metadata.content_rating = ' '

            # Create a cast array
            cast_array = json_recording_details['cast']
            show_id = json_recording_details['metadata']['show_id']

            ## Prepare media db api query 
            ## TODO: Fix url once API is ready
            media_db_api_url = "https://stagemedia.me/api/images?show_id={}&actor_ids={}".format(show_id, ','.join([str(x['performer']['id']) for x in cast_array]))
            Log(u'[Encora] Media DB API URL: {}'.format(media_db_api_url))
            ## make request to mediadb for poster / headshots
            headers = {
                'Authorization': 'Bearer {}'.format(stagemedia_api_key()),
                'User-Agent': 'PlexAgent/0.9'
            }
            request = urllib2.Request(media_db_api_url, headers=headers)
            response = urllib2.urlopen(request)
            api_response = json.load(response)
            Log('[Encora] Media DB API response: {}'.format(api_response))

            # Update genres based on recording type
            metadata.genres.clear()
            recording_type = json_recording_details['metadata']['recording_type']
            if recording_type:
                metadata.genres.add(recording_type)
            if json_recording_details['metadata']['media_type']:
                metadata.genres.add(json_recording_details['metadata']['media_type'])
                Log(u'[Encora] added genre {}'.format(json_recording_details['metadata']['media_type']))

            def get_order(cast_member):
                return cast_member['character'].get('order', 999) if cast_member['character'] else 999
            
            performer_url_map = {performer['id']: performer['url'] for performer in api_response['performers']}

            for key in metadata.posters.keys():
                del metadata.posters[key]
            
            # set the posters from API
            if 'posters' in api_response:
                for full_poster_url in api_response['posters']:
                    # log each URL
                    Log(u'[Encora] Full Poster URL: {}'.format(full_poster_url))
                    metadata.posters[full_poster_url] = Proxy.Preview(HTTP.Request(full_poster_url).content)

            sorted_cast = sorted(json_recording_details['cast'], key=get_order)
            metadata.roles.clear()
            for cast_member in sorted_cast:
                role = metadata.roles.new()
                role.name = cast_member['performer']['name']  # Performer name = role.name
                if cast_member['status']:
                    role.role = cast_member['status']['abbreviation'].lower() + ' ' + cast_member['character']['name']  # Character status + name = role.role
                else:
                    role.role = cast_member['character']['name'] if cast_member['character'] else "Ensemble"  # Character name = role.role
                
                # Assign the performer's photo URL if it exists or use the Imgur link if URL is null
                performer_id = cast_member['performer']['id']
                performer_url = cast_member['performer']['url']
                
                if performer_id in performer_url_map:
                    if performer_url_map[performer_id] != None:
                        role.photo = performer_url_map[performer_id]
                    else:
                        role.photo = "https://i.imgur.com/cXqYZEu.png"
                else:
                    role.photo = performer_url

            if Prefs['add_master_as_director']:
                metadata.directors.clear()
                try:
                    meta_director = metadata.directors.new()
                    meta_director.name = json_recording_details['master']
                    Log(u'[Encora] add_master_as_director: {}'.format(json_recording_details['master']))
                except Exception as e:
                    Log.Info(u'[Encora]  add_master_as_director exception: {}'.format(e))
            return
    except Exception as e:
        tb = traceback.format_exc()
        Log(u'[Encora] update() - Could not retrieve data from Encora API for: "{}", Exception: "{}"'.format(recording_id, e))
        Log(u'[Encora] update() - Traceback: {}'.format(tb))

    Log('=== End Of Agent Call, errors after that are Plex related ==='.ljust(157, '='))

    ### Movie - API call ################################################################################################################
    Log(u'[Encora] update() using api - dir: {}, metadata.id: {}'.format(dir, metadata.id))
    try:
        json_recording_details = json_load(ENCORA_API_RECORDING_INFO, guid)
    except Exception as e:
        tb = traceback.format_exc()
        Log(u'[Encora] update() - Could not retrieve data from Encora API for: "{}", Exception: "{}"'.format(recording_id, e))
        Log(u'[Encora] update() - Traceback: {}'.format(tb))
    else:
        Log('[Encora] Movie mode - json_recording_details - Loaded recording details from: "{}"'.format(ENCORA_API_RECORDING_INFO.format(guid, 'personal_key')))
        date = Datetime.ParseDate(json_recording_details['date']['full_date'])
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
        metadata.year = date.year
        Log(u'[Encora] year: {}'.format(date.year))
        
        # Set content rating based on NFT status
        nft_date = json_recording_details['nft']['nft_date']
        nft_forever = json_recording_details['nft']['nft_forever']

        # Parse the nft_date in ISO 8601 format
        nft_date_parsed = parse_iso8601(nft_date) if nft_date else None

        # Get the current time in UTC (naive datetime)
        current_time = datetime.utcnow()

        # Compare only when nft_date is present and properly parsed
        if nft_forever or (nft_date_parsed and nft_date_parsed > current_time):
            metadata.content_rating = 'NFT'
        else:
            metadata.content_rating = ' '

        def get_order(cast_member):
            return cast_member['character'].get('order', 999) if cast_member['character'] else 999
        sorted_cast = sorted(json_recording_details['cast'], key=get_order)
        metadata.roles.clear()
        for cast_member in sorted_cast:
            role = metadata.roles.new()
            role.name = cast_member['performer']['name'] # Performer name = role.name
            if cast_member['status']:
                role.role = cast_member['status']['abbreviation'].lower() + ' ' + cast_member['character']['name'] # Character status + name = role.role
            else:
                role.role = cast_member['character']['name'] if cast_member['character'] else "Ensemble" # Character name = role.role
            #role.photo = cast_member['performer']['url'] # this needs to query new headshot database
        if Prefs['add_master_as_director']:
            metadata.directors.clear()
            try:
                meta_director = metadata.directors.new()
                meta_director.name = json_recording_details['master']
            except Exception as e:
                Log.Info(u'[Encora] add_master_as_director exception: {}'.format(e))
        return
    
    Log('=== End Of Agent Call, errors after that are Plex related ==='.ljust(157, '='))

### Agent declaration ##################################################################################################################################################
class EncoraAgent(Agent.Movies):
  name, primary_provider, fallback_agent, contributes_to, accepts_from, languages = 'Encora', True, ['com.plexapp.agents.xbmcnfo'], None, ['com.plexapp.agents.xbmcnfo'], [Locale.Language.NoLanguage]
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
