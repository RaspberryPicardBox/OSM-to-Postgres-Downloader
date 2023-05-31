import requests
import tqdm
import os

RECUSIVE_DOWNLOAD_FLAG = 0

SIMPLE_LUA_CONTENT = """-- This config example file is released into the Public Domain.

-- This is a very simple Lua config for the Flex output not intended for
-- real-world use. Use it do understand the basic principles of the
-- configuration. After reading and understanding this, have a look at
-- "geometries.lua".

-- For debugging
-- inspect = require('inspect')

-- The global variable "osm2pgsql" is used to talk to the main osm2pgsql code.
-- You can, for instance, get the version of osm2pgsql:
print('osm2pgsql version: ' .. osm2pgsql.version)

-- A place to store the SQL tables we will define shortly.
local tables = {}

schema = ''

-- This is an "area table", it can contain data derived from ways or relations
-- and will contain an "area_id" column. Way ids will be stored "as is" in the
-- "area_id" column, for relations the negative id will be stored. When
-- running in "append" mode, osm2pgsql will automatically update this table
-- using the way/relation ids.
tables.polygons_buildings = osm2pgsql.define_table({
    name='buildings',
    ids = { type = 'area', id_column = 'osm_id' },
    columns = {
        { column = 'ogc_fid', sql_type = 'serial', create_only = true },
        { column = 'name', type = 'text' },
        { column = 'fclass', type = 'text'},
        { column = 'type', type = 'text'},
        { column = 'tags', type = 'jsonb'},
        { column = 'geom', type = 'multipolygon', not_null = true, projection=4326 }
    },
    schema = schema
})

tables.pois = osm2pgsql.define_table({
    name='pois',
    ids = { type = 'node', id_column = 'osm_id'},
    columns = {
        { column = 'ogc_fid', sql_type = 'serial', create_only = true },
        { column = 'name', type = 'text'},
        { column = 'fclass', type = 'text'},
        { column = 'type', type = 'text'},
        { column = 'tags', type = 'jsonb'},
        { column = 'geom', type = 'point', not_null = true, projection=4326 }
    },
    schema = schema
})

tables.way_roads = osm2pgsql.define_table({
    name='roads',
    ids = { type = 'way', id_column = 'osm_id' },
    columns = {
        { column = 'ogc_fid', sql_type = 'serial', create_only = true },
        { column = 'name', type = 'text' },
        { column = 'fclass', type = 'text'},
        -- The type of the `geom` column is `multilinestring`, because we need to store
        -- linestrings and outlines (possibly)
        { column = 'geom', type = 'multilinestring', not_null = true, projection=4326 }
    },
    schema = schema
})

-- These tag keys are generally regarded as useless for most rendering. Most
-- of them are from imports or intended as internal information for mappers.
--
-- If a key ends in '*' it will match all keys with the specified prefix.
--
-- If you want some of these keys, perhaps for a debugging layer, just
-- delete the corresponding lines.
local delete_keys = {
    -- "mapper" keys
    'attribution',
    'comment',
    'created_by',
    'fixme',
    'note',
    'note:*',
    'odbl',
    'odbl:note',
    'source',
    'source:*',
    'source_ref',

    -- "import" keys

    -- Corine Land Cover (CLC) (Europe)
    'CLC:*',

    -- Geobase (CA)
    'geobase:*',
    -- CanVec (CA)
    'canvec:*',

    -- osak (DK)
    'osak:*',
    -- kms (DK)
    'kms:*',

    -- ngbe (ES)
    -- See also note:es and source:file above
    'ngbe:*',

    -- Friuli Venezia Giulia (IT)
    'it:fvg:*',

    -- KSJ2 (JA)
    -- See also note:ja and source_ref above
    'KSJ2:*',
    -- Yahoo/ALPS (JA)
    'yh:*',

    -- LINZ (NZ)
    'LINZ2OSM:*',
    'linz2osm:*',
    'LINZ:*',
    'ref:linz:*',

    -- WroclawGIS (PL)
    'WroclawGIS:*',
    -- Naptan (UK)
    'naptan:*',

    -- TIGER (US)
    'tiger:*',
    -- GNIS (US)
    'gnis:*',
    -- National Hydrography Dataset (US)
    'NHD:*',
    'nhd:*',
    -- mvdgis (Montevideo, UY)
    'mvdgis:*',

    -- EUROSHA (Various countries)
    'project:eurosha_2012',

    -- UrbIS (Brussels, BE)
    'ref:UrbIS',

    -- NHN (CA)
    'accuracy:meters',
    'sub_sea:type',
    'waterway:type',
    -- StatsCan (CA)
    'statscan:rbuid',

    -- RUIAN (CZ)
    'ref:ruian:addr',
    'ref:ruian',
    'building:ruian:type',
    -- DIBAVOD (CZ)
    'dibavod:id',
    -- UIR-ADR (CZ)
    'uir_adr:ADRESA_KOD',

    -- GST (DK)
    'gst:feat_id',

    -- Maa-amet (EE)
    'maaamet:ETAK',
    -- FANTOIR (FR)
    'ref:FR:FANTOIR',

    -- 3dshapes (NL)
    '3dshapes:ggmodelk',
    -- AND (NL)
    'AND_nosr_r',

    -- OPPDATERIN (NO)
    'OPPDATERIN',
    -- Various imports (PL)
    'addr:city:simc',
    'addr:street:sym_ul',
    'building:usage:pl',
    'building:use:pl',
    -- TERYT (PL)
    'teryt:simc',

    -- RABA (SK)
    'raba:id',
    -- DCGIS (Washington DC, US)
    'dcgis:gis_id',
    -- Building Identification Number (New York, US)
    'nycdoitt:bin',
    -- Chicago Building Inport (US)
    'chicago:building_id',
    -- Louisville, Kentucky/Building Outlines Import (US)
    'lojic:bgnum',
    -- MassGIS (Massachusetts, US)
    'massgis:way_id',
    -- Los Angeles County building ID (US)
    'lacounty:*',
    -- Address import from Bundesamt für Eich- und Vermessungswesen (AT)
    'at_bev:addr_date',

    -- misc
    'import',
    'import_uuid',
    'OBJTYPE',
    'SK53_bulk:load',
    'mml:class'
}

-- The osm2pgsql.make_clean_tags_func() function takes the list of keys
-- and key prefixes defined above and returns a function that can be used
-- to clean those tags out of a Lua table. The clean_tags function will
-- return true if it removed all tags from the table.
local clean_tags = osm2pgsql.make_clean_tags_func(delete_keys)

-- Helper function that looks at the tags and decides if this is possibly
-- an area.
function has_area_tags(tags)
    if tags.area == 'yes' then
        return true
    end
    if tags.area == 'no' then
        return false
    end

    return tags.aeroway
        or tags.amenity
        or tags.building
        or tags.harbour
        or tags.historic
        or tags.landuse
        or tags.leisure
        or tags.man_made
        or tags.military
        or tags.natural
        or tags.office
        or tags.place
        or tags.power
        or tags.public_transport
        or tags.shop
        or tags.sport
        or tags.tourism
        or tags.water
        or tags.waterway
        or tags.wetland
        or tags['abandoned:aeroway']
        or tags['abandoned:amenity']
        or tags['abandoned:building']
        or tags['abandoned:landuse']
        or tags['abandoned:power']
        or tags['area:highway']
        or tags['building:part']
end

-- Helper function to remove some of the tags we usually are not interested in.
-- Returns true if there are no tags left.
function clean_tags(tags)
    tags.odbl = nil
    tags.created_by = nil
    tags.source = nil
    tags['source:ref'] = nil

    return next(tags) == nil
end


-- Called for every way in the input. The `object` argument contains the same
-- information as with nodes and additionally a boolean `is_closed` flag and
-- the list of node IDs referenced by the way (`object.nodes`).
function osm2pgsql.process_way(object)
    --  Uncomment next line to look at the object data:
    -- print(inspect(object))

    if clean_tags(object.tags) then
        return
    end

    if object.is_closed and has_area_tags(object.tags) and object.tags.building then

        if object.tags.building == 'yes' then
            building_type = nil
        else
            building_type = object.tags.building
        end

        if object.tags.type == nil then
            object_type = 'building'
        else
            object_type = object.tags.type
        end

        tables.polygons_buildings:insert({
            name = object.tags['name'],
            fclass = object_type,
            type = building_type,
            tags = object.tags,
            geom = object:as_multipolygon()
        })

    elseif object.tags.highway then

        tables.way_roads:insert({
            name = object.tags['name'],
            fclass = object.tags.highway,
            geom = object:as_multilinestring()
        })

    end
end

function osm2pgsql.process_node(object)
    if clean_tags(object.tags) then
    return
    end
    
    if object.tags.name or object.tags.shop then
        tables.pois:insert({
            name = object.tags['name'],
            fclass = object_type,
            type = building_type,
            tags = object.tags,
            geom = object:as_point()
        })
    end
end
"""


def download_file(url, country, possible_file_types, force_pbf):
    global RECUSIVE_DOWNLOAD_FLAG

    chunk_size = 8192
    RECUSIVE_DOWNLOAD_FLAG += 1

    if RECUSIVE_DOWNLOAD_FLAG > 5:
        print("Either an incorrect input was entered too many times, or a serious error has occurred. Closing program.")
        quit()
    elif RECUSIVE_DOWNLOAD_FLAG > 0:
        overwrite = None
        url = url.replace(possible_file_types[0], '')
        url = url.replace(possible_file_types[1], '')

    if force_pbf:
        print("PBF is being forced!")
        try:
            url += possible_file_types[1]
            local_filename = f"{country}-latest" + possible_file_types[1]
            total = round(int(requests.head(url).headers['Content-Length']) / chunk_size)
            print("Found an osm.pbf file, downloading...")
        except KeyError:
            return
    else:
        print("PBF is not being forced; checking for available file.")
        try:
            url += possible_file_types[0]
            local_filename = f"{country}-latest" + possible_file_types[0]
            total = round(int(requests.head(url).headers['Content-Length']) / chunk_size)
            print("Found a shp.zip file, downloading that...")
        except KeyError:
            try:
                url = url.replace(possible_file_types[0], '')
                url += possible_file_types[1]
                local_filename = f"{country}-latest" + possible_file_types[1]
                total = round(int(requests.head(url).headers['Content-Length']) / chunk_size)
                print("Found an osm.pbf file, downloading...")
            except KeyError:
                return

    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        try:
            open(local_filename, 'r')
            overwrite = input(f'A file with that name ({local_filename}) was already found. Would you like to '
                              f'overwrite it? Y/n\n')
            if overwrite.lower() == 'y' or overwrite.lower() == 'yes':
                raise FileNotFoundError
            elif overwrite.lower() == 'n' or overwrite.lower() == 'no':
                print("Continuing with pre-downloaded file...")
                return local_filename
            else:
                print("That input is invalid... Please try again.")
                download_file(url, country, possible_file_types)
        except FileNotFoundError:
            with open(local_filename, 'wb') as f:
                for chunk in tqdm.tqdm(r.iter_content(chunk_size=chunk_size), total=total):
                    f.write(chunk)
    return local_filename


if __name__ == "__main__":

    region = input('Please input a valid region for download.geofabrik.de: ')
    country = input('Please input a valid country for download.geofabrik.de: ')

    schema = input('Please enter a schema name: ')

    pghost = input('Please enter a host IP (default: 127.0.0.1): ')
    if len(pghost) < 1:
        pghost = '127.0.0.1'
    port = input('Please enter a port (default: 5432): ')
    if len(port) < 1:
        port = 5432
    pgdb = input('Please enter a database name (default: db): ')
    if len(pgdb) < 1:
        pgdb = 'db'

    pguser = input('Please enter a user name: (default: user)')
    if len(pguser) < 1:
        pguser = 'user'
    password = input('Please enter a password '
                     '(Please note, this will be asked for a second time if an OGC file is found): ')

    force_tags = input('Do you want to force download the OGC file with tags? (y/N)')

    if force_tags.lower() == 'y':
        tags = True
    else:
        tags = False

    url = f"https://download.geofabrik.de/{region}/{country}-latest"
    possible_file_types = ["-free.shp.zip", ".osm.pbf"]

    print("Pre-processing database and schema folder...")
    os.system("rm -rf ./" + schema)
    if password:
        os.system(
            f"psql postgres://{pguser}:{password}@{pghost}:{port}/{pgdb} -c 'drop schema if exists {schema} cascade'; ")
        os.system(f"psql postgres://{pguser}:{password}@{pghost}:{port}/{pgdb} -c 'create schema {schema}'; ")
    else:
        os.system(f"psql postgres://{pguser}@{pghost}:{port}/{pgdb} -c 'drop schema if exists {schema} cascade'; ")
        os.system(f"psql postgres://{pguser}@{pghost}:{port}/{pgdb} -c 'create schema {schema}'; ")

    print(f"Downloading from {url}...")
    if tags:
        filename = download_file(url, country, possible_file_types, True)
    else:
        filename = download_file(url, country, possible_file_types, False)

    if not filename:
        print('The region or country were incorrect and a file could not be found. Please try again!')
        quit()

    if filename.endswith(possible_file_types[0]):
        print("Making a new directory for the zip file...")
        try:
            os.mkdir('./' + schema)
        except FileExistsError:
            pass

        print("Unzipping the zip file...")
        os.system(f"cp {filename} ./{schema}")
        os.system(f"cd ./{schema} && unzip {filename}")

        for file in os.listdir('./' + schema):
            if file.endswith('.shp'):
                print(f"Processing and uploading {file}...")
                if password:
                    if '_a_' not in file:
                        os.system(f"cd ./{schema} && ogr2ogr -f PostgreSQL 'PG:host={pghost} port={port} dbname={pgdb} "
                                  f"user={pguser} password={password}' -lco SCHEMA={schema} {file}")
                    else:
                        os.system(f"cd ./{schema} && ogr2ogr -f PostgreSQL 'PG:host={pghost} port={port} dbname={pgdb} "
                                  f"user={pguser} password={password}' -nlt PROMOTE_TO_MULTI "
                                  f"-lco SCHEMA={schema} {file}")
                else:
                    if '_a_' not in file:
                        os.system(
                            f"cd ./{schema} && ogr2ogr -f PostgreSQL 'PG:host={pghost} port={port} dbname={pgdb} "
                            f"user={pguser}' -lco SCHEMA={schema} {file}")
                    else:
                        os.system(
                            f"cd ./{schema} && ogr2ogr -f PostgreSQL 'PG:host={pghost} port={port} dbname={pgdb} "
                            f"user={pguser}' -nlt PROMOTE_TO_MULTI -lco SCHEMA={schema} {file}")

        print(f"Completed download and import of {filename} into {pgdb} schema {schema}!")

    elif filename.endswith(possible_file_types[1]):
        print(f'Processing and uploading {filename}...')

        with open('simple.lua', 'w') as f:
            new_content = SIMPLE_LUA_CONTENT.replace("schema = ''", f"schema = '{schema}'")
            f.write(new_content)
            f.close()

        if password:
            os.system(
                f"osm2pgsql -c --database={pgdb} --user={pguser} --host={pghost} --port={port} --password -O flex -S "
                f"simple.lua"
                f"{filename}")
        else:
            os.system(
                f"osm2pgsql -c --database={pgdb} --user={pguser} --host={pghost} --port={port} -O flex -S simple.lua "
                f"{filename}")

        os.system("rm ./simple.lua")
        print(f"Completed download and import of {filename} into {pgdb} schema {schema}!")
