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

  class GoogleTransitFeed
    def initialize directory, verbose=false
      @files = {}

      FEED_FILES.each do |file|
        @files[file] = GoogleTransitFeedFile.new "#{directory}/#{file}.txt", verbose
      end
    end

    def [] file
      @files[file]
    end
  end

  class GoogleTransitFeedFile
    attr_reader :header, :data

    def initialize file, verbose=false
      print "Parsing #{file}\n" if verbose

      @header = []
      @data = []

      begin
        contents = File.read file
      rescue
        return nil
      end

      #check if file is tainted by quotes
      has_quotes = true if contents.match(/"/) else false

      contents = contents.split("\n")
      fsize = contents.size

      @header = split_csv_with_quotes( contents.shift )

      i=0
      if has_quotes then
        @data = contents.collect do |line|
          i += 1
          if verbose and i%5000==0 then
            print "#{(Float(i)/fsize)*100}%\n"
          end

          split_csv_with_quotes( line )
        end
      else
        @data = contents.collect do |line|
          i += 1
          if verbose and i%5000==0 then
            print "#{(Float(i)/fsize)*100}%\n"
          end

          line.split(",").collect do |element| element.strip end 
        end
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
