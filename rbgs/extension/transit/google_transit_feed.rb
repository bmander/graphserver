module GoogleTransitFeed

  #parse the form "YYYY-MM-DD"
  #returns that date in UTC
  def self.parse_date date
    Time.utc( date[0..3], date[5..6], date[8..9], 0, 0, 0, 0 )
  end

  #parse the form "HH:MM:SS"
  #returns seconds since beginning of local midnight
  def self.parse_time time
    time[0..1].to_i*3600 + time[3..4].to_i*60 + time[6..7].to_i
  end

  FEED_FILES = [["agency",          ["agency_id","agency_name","agency_url","agency_timezone","agency_lang"]],
                ["stops",           ["stop_id","stop_name","stop_desc","stop_lat","stop_lon","zone_id","stop_url","stop_code"]],
                ["routes",          ["route_id","agency_id","route_short_name","route_long_name","route_desc","route_type","route_url","route_color","route_text_color"]],
                ["trips",           ["route_id","service_id","trip_id","trip_headsign","direction_id","block_id","shape_id"]],
                ["stop_times",      ["trip_id","arrival_time","departure_time","stop_id","stop_sequence","stop_headsign","pickup_type","drop_off_type","shape_dist_traveled"]],
                ["calendar_dates",  ["service_id","date","exception_type"]],
                ["fare_attributes", ["fare_id","price","currency_type","payment_method","transfers","transfer_duration"]],
                ["fare_rules",      ["fare_id","route_id","origin_id","destination_id","contains_id"]],
                ["shapes",          ["shape_id","shape_pt_lat","shape_pt_lon","shape_pt_sequence"]]]
  OPTIONAL_FEED_FILES = [["calendar",    ["service_id","monday","tuesday","wednesday","thursday","friday","saturday","sunday","start_date","end_date"]],
                         ["frequencies", ["trip_id","start_time","end_time","headway_secs"]]]
  #IDs that should be unique in its namespace
  U_IDS = ["stop_id", "route_id", "service_id", "trip_id", "fare_id", "shape_id"]

  class GoogleTransitFeed
    attr_reader :namespace

    def initialize directory, verbose=false
      @files = {}

      #The namespace of the feed is the first agency of the agency.txt file
      f = File.new("#{directory}/agency.txt")
      @namespace = f.read.split("\n")[1].split( "," )[0]
      puts "Namespace for the feed = #{@namespace}"
      f.close

      FEED_FILES.each do |file, fields|
        @files[file] = GoogleTransitFeedFile.new "#{directory}/#{file}.txt", fields
      end

      OPTIONAL_FEED_FILES.each do |file, fields|
        begin
          @files[file] = GoogleTransitFeedFile.new "#{directory}/#{file}.txt", fields
        rescue
        end
      end
    end

    def [] file
      @files[file]
    end

  end

  class GoogleTransitFeedFile
    attr_reader :format, :header

    def initialize filename, format
      #Read header and leave file open
      @format = format
      @fp = File.new( filename )
      @header = split_csv_with_quotes( @fp.readline )

      #create a map whereby each heading of the @format is mapped to its index in @header, or nil
      @formatmap = []
      @format.each_with_index do |field, i|
        @formatmap << @header.index(field)
      end
    end

    def each_line
      @fp.each_line do |line|
        splitline = split_csv_with_quotes( line )

        reformed = []
        @formatmap.each do |pt|
          if pt.nil? then
            reformed << ""
          else
            reformed << splitline[pt]
          end
        end

        #p reformed

        yield reformed
      end
    end

    #Reads a line from file and converts to fields
    def get_row
      line = @f.gets
      #if eof return nil
      if line == nil then return nil end
      #if line has quotes
      if line.match(/"/) then
        splitline = split_csv_with_quotes( line )
      else
        splitline = line.split(",").collect do |element| element.strip end
      end

      # Reorder columns according to the formatmap
      reformed = []
      @formatmap.each do |pt|
        if pt.nil? then
          reformed << ""
        else
          reformed << splitline[pt]
        end
      end
      return reformed
    end

private

    def split_csv_with_quotes string
      quote = Regexp.compile( /"/ )
      fields = string.split( "," )

      i = 0
      n = fields.size

      while i < n do
        # if a field has an unevent number of quotes
        # merge it with the next field
        if fields[i].scan( quote ).size%2 != 0 then
          fields[i..i+1] = fields[i] + (fields[i+1] or "")
          n -= 1
        end
        fields[i].strip!
        i += 1
      end

      return fields
    end
  end
end
