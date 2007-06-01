module TigerLine
  RT1_format = "A1A4A10A1A1A2A30A4A2A3A11A11A11A11A1A1A1A1A5A5A5A5A1A1A1A1A2A2A3A3A5A5A5A5A5A5A6A6A4A4A10A9A10A9"
  RT2_format = "A1A4A10A3A10A9A10A9A10A9A10A9A10A9A10A9A10A9A10A9A10A9A10A9"
  RTI_format = "A1A4A5A10A10A10A5A10A5A10A1017A10A10A10"

  class TigerFile
    attr_reader :data

    def initialize filename
      @data = nil
      @filename = filename
      @format = "A*"
    end

    def read
      @data = []
 
      fp_size = File.size @filename
      fp = File.new @filename, "r"
      i=0
      fp.each_line do |line|
        if i%5000 == 0 then print sprintf("%.1f", (Float(fp.pos)/fp_size)*100 ) + "%\n" end

        @data << line.unpack(@format)

        i += 1
      end
      fp.close
    end

    def each_record
      unless @data then
        return nil
      end

      @data.each do |record|
        yield record
      end
    end
  end

  class RT1File < TigerFile
    def initialize filename
      super filename
      @format = RT1_format
    end

    def read
      super
      indexed_data = {}
      @data.each do |data_line|
        tlid = data_line[2].strip
        indexed_data[ tlid ] = data_line
      end
      @data = indexed_data
    end
  end

  class RT2File < TigerFile
    def initialize filename
      super filename
      @format = RT2_format
    end

    def read
      super
      indexed_data = {}
      @data.each do |data_line|
        tlid = data_line[2].strip
        indexed_data[ tlid ] ||= []
        10.times do |i|
          long = Float( data_line[4+2*i].insert(4, ".") )
          lat  = Float( data_line[4+2*i+1].insert(3, ".") )
          if lat!=0 and long!=0 then
            indexed_data[tlid] << [long, lat]
          end
        end
      end
      @data = indexed_data
    end
  end 

  class RTIFile < TigerFile
    def initialize filename
      super filename
      @format = RTI_format
    end

    def read
      super

      indexed_data = {}
      @data.each do |data_line|
        tlid = data_line[3].strip
        indexed_data[ tlid ] = data_line
      end
      @data = indexed_data
    end
  end

  class TigerFeature
    attr_accessor :tlid, :fedirp, :fename, :fetype, :fedirs, :cfcc, :tzids, :tzide, :points

    def line_wkt
      ret = "LINESTRING("
      points.each do |long, lat|
        ret << "#{long} #{lat}, "
      end
      ret[-2..-1]=')'
      return ret
    end
  end

  class TigerLine
    attr_reader :filename_base

    def initialize directory
      @features = nil
      @filename_base = Dir["#{directory}/*.RT1"].first
      if @filename_base then
        @filename_base = @filename_base.split(".").first
      end
      return @filename_base
    end

    def read
      @features = {}

      rt1_file = RT1File.new( @filename_base + ".RT1" )
      rt2_file = RT2File.new( @filename_base + ".RT2" )
      rti_file = RTIFile.new( @filename_base + ".RTI" )

      #get the tlid for each feature
      print "Reading Complete Chain Basic Data Record...\n"
      rt1_file.read
      rt1_file.each_record do |tlid, record|
        start_point = [ Float( record[40].insert(4, ".") ), Float( record[41].insert(3, ".") ) ]
        end_point = [ Float( record[42].insert(4, ".") ), Float( record[43].insert(3, ".") ) ]

        feature = TigerFeature.new
        feature.tlid = tlid
        feature.fedirp = record[5].strip
        feature.fename = record[6].strip
        feature.fetype = record[7].strip
        feature.fedirs = record[8].strip
        feature.cfcc = record[9].strip
        feature.points = [start_point, end_point]
        @features[ tlid ] = feature
      end

      #get the feature geometry
      print "Reading Shape Coordinates...\n"
      rt2_file.read
      rt2_file.each_record do |record|
        feature = @features[ record[0] ]
        unless feature then next end
        if record[1] then
          feature.points = [feature.points.first] + record[1] + [feature.points.last]
        end
      end

      #get feature endpoints
      print "Reading Endpoint Nodes...\n"
      rti_file.read
      rti_file.each_record do |record|
        feature = @features[ record[0] ]
        unless feature then next end
        feature.tzids = record[1][4].strip
        feature.tzide = record[1][5].strip
      end
    end

    def each_feature
      @features.each_pair do |tlid, feature|
        yield feature
      end
    end

  end

end
