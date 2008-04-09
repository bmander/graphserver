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

  FEED_FILES = ["agency", "stops", "routes", "trips", "stop_times", "calendar", "calendar_dates", "fare_attributes", "fare_rules", "shapes", "frequencies"]
  #IDs that should be unique in its namespace
  U_IDS = ["stop_id", "zone_id", "route_id", "service_id", "trip_id", "fare_id", "shape_id"]

  class GoogleTransitFeed
    attr_reader :namespace

    def initialize directory
      @files = {}

      #The namespace of the feed is the first agency of the agency.txt file
      f = File.new("#{directory}/agency.txt")
      @namespace = f.read.split("\n")[1].split( "," )[0]
      puts "namespace = #{@namespace}"
      f.close

      #Init files
      FEED_FILES.each do |file|
        @files[file] = GoogleTransitFeedFile.new "#{directory}/#{file}.txt"
      end

    end

    def [] file
      @files[file]
    end
  end

  class GoogleTransitFeedFile
    attr_reader :header

    #Read header and leave file open
    def initialize file
      @header = []
      @f = []

      @f = File.new(file)
      @header = split_csv_with_quotes( @f.gets )
      #The file remains open...
    end

    #Reads a line from file and converts to fields
    def get_row
      line = @f.gets
      #if eof return nil
      if line == nil then return nil end
      #if line has quotes
      if line.match(/"/) then
        split_csv_with_quotes( line )
      else
        line.split(",").collect do |element| element.strip end
      end
    end

    private

    def split_csv_with_quotes string
      quote = Regexp.compile( /"/ )
      fields = string.split( "," )

      i = 0
      n = fields.size

      while i < n do
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
