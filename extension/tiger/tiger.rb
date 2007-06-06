module TigerLine
  #Complete Chain Basic Data Record
  RT1_fields = [[:rs, 1], [:version, 4], [:tlid, 10], [:side1, 1], [:source, 1], [:fedirp, 2], [:fename, 30], [:fetype, 4], [:fedirs, 2], [:cfcc, 3], [:fraddl, 11], [:toaddl, 11], [:fraddr, 11], [:toaddr, 11], [:friaddl, 1], [:toiaddl, 1], [:friaddr, 1], [:toiaddr, 1], [:zipl, 5], [:zipr, 5], [:aianhhfpl, 5], [:aianhhfpr, 5], [:aihhtlil, 1], [:aihhtlir, 1], [:census1, 1], [:census2, 1], [:statel, 2], [:stater, 2], [:countyl, 3], [:countyr, 3], [:cousubl, 5], [:cousubr, 5], [:submcdl, 5], [:submcdr, 5], [:placel, 5], [:placer, 5], [:tractl, 6], [:tractr, 6], [:blockl, 4], [:blockr, 4], [:frlong, 10], [:frlat, 9], [:tolong, 10], [:tolat, 9]]
  #Complete Chain Shape Coordinates
  RT2_fields = [[:rt, 1], [:version, 4], [:tlid, 10], [:rtsq, 3], [:long1, 10], [:lat1, 9], [:long2, 10], [:lat2, 9], [:long3, 10], [:lat3, 9], [:long4, 10], [:lat4, 9], [:long5, 10], [:lat5, 9], [:long6, 10], [:lat6, 9], [:long7, 10], [:lat7, 9], [:long8, 10], [:lat8, 9], [:long9, 10], [:lat9, 9], [:long10, 10], [:lat10, 9]]
  #Index to Alternate Feature Identifiers
  RT4_fields = [[:rt, 1], [:version, 4], [:tlid, 10], [:rtsq, 3], [:feat1, 8], [:feat2, 8], [:feat3, 8], [:feat4, 8], [:feat5, 8]]
  #Complete Chain Feature Identifiers
  RT5_fields = [[:rt, 1], [:version, 4], [:file, 5], [:feat, 8], [:fedirp, 2], [:fename, 30], [:fetype, 4], [:fedirs, 2]]
  #Additional Address Range and ZIP Code Data
  RT6_fields = [[:rt, 1], [:version, 4], [:tlid, 10], [:rtsq, 3], [:fraddl, 11], [:toaddl, 11], [:fraddr, 11], [:toaddr, 11], [:friaddl, 1], [:toiaddl, 1], [:friaddr, 1], [:toiaddr, 1], [:zipl, 5], [:zipr, 5]]
  #Link Between Complete Chains And (Link Between) Polygons
  RTI_fields = [[:rt, 1], [:version, 4], [:file, 5], [:tlid, 10], [:tzids, 10], [:tzide, 10], [:cenidl, 5], [:polyidl, 10], [:cenidr, 5], [:polyidr, 10], [:rsi4, 10], [:ftseg, 17], [:rsi1, 10], [:rsi2, 10], [:rsi3, 10]]

  #==========Number Parsing Helper Methods===========

  class Helper
    LONG_DEC_POS = 4
    LAT_DEC_POS = 3

    #decimal numbers are stored in TIGER with an implied accuracy
    def self.parse_number str, point_pos
      str.insert(point_pos, ".").to_f
    end

    def self.parse_long str
      self.parse_number( str, LONG_DEC_POS )
    end

    def self.parse_lat str
      self.parse_number( str, LAT_DEC_POS )
    end
  end

  #A Record is an array of values and a hash of field names to array indices, and is used like a Hash.
  #Since the ordinal hash can be shared by reference by a large number of arrays, it is more lightweight
  #than a large number of hashes with identical sets of keys.
  class Record
    #this, and the self.class.etc nonsense is a trick to make non-inheritable class variables
    class <<self; attr_accessor :format, :ordinals end
    @format = ""    #passed to string.unpack to split up raw_data
    @ordinals = {}  #hash of {fieldname => ordinal}

    def initialize raw_data  #a string of fixed-length fields
      @data = raw_data.unpack( self.class.format ).map do |field| field.strip end
    end

    def [] name
      @data[ self.class.ordinals[ name ] ]
    end

    #This class is a pretend hash. This method returns a real hash, but it's relatively expensive
    def to_hash
      ret = {}
      self.class.ordinals.each do |key, value|
        ret[key] = @data[value]
      end
      ret
    end

    def inspect
      to_hash.inspect
    end

  private
    class <<self
      def fields= fields
        @format = fields.map do |field| "A"+field.last.to_s end.join
        @ordinals = {}
        fields.each_with_index do |field, i|
          @ordinals[field.first] = i
        end
      end
    end
  end

  class RT1 < Record
    self.fields= RT1_fields

    attr_accessor :rt2_records, :rt4_records, :rt6_records, :rti_record

    def initialize raw_data
      super raw_data

      @rt2_records = []
      @rt4_records = []
      @rt6_records = []
    end
  end

  class RT2 < Record
    self.fields= RT2_fields
  end

  class RT4 < Record
    self.fields= RT4_fields

    attr_accessor :rt5_records

    def initialize raw_data
      super raw_data

      @rt5_records = []
    end
  end

  class RT5 < Record
    self.fields= RT5_fields
  end

  class RT6 < Record
    self.fields= RT6_fields
  end

  class RTI < Record
    self.fields= RTI_fields
  end

  class RecordFile
    def self.read filename, record_class, key_field=nil
      print "Loading and parsing record type #{record_class.inspect}\n"
      if key_field then
        @records = {}
      else
        @records = []
      end
 
      fp_size = File.size filename
      fp = File.new filename, "r"
      i=0
      fp.each_line do |line|
        if i%5000 == 0 then print sprintf("%.1f", (Float(fp.pos)/fp_size)*100 ) + "%\n" end

        record = record_class.new( line )
        if key_field then
          @records[ record[ key_field ] ] = record
        else
          @records << record
        end

        i += 1
      end
      fp.close

      @records
    end
  end

  class Feature
    attr_accessor :tlid, :tzids, :tzide, :addess_ranges, :names, :cfcc, :points
 
    def initialize rt1_record
      #tlid
      @tlid = rt1_record[:tlid]
      #tzids, tzide
      @tzids = rt1_record.rti_record[:tzids]
      @tzide = rt1_record.rti_record[:tzide]
      #address_ranges
      @address_ranges = []
      @address_ranges << {:fraddl => rt1_record[:fraddl], 
                          :toaddl => rt1_record[:toaddl], 
                          :fraddr => rt1_record[:fraddr], 
                          :toaddr => rt1_record[:toaddr]} if not rt1_record[:fraddl].empty?
      rt1_record.rt6_records.each do |rt6_record|
        @address_ranges << {:fraddl => rt6_record[:fraddl], 
                            :toaddl => rt6_record[:toaddl], 
                            :fraddr => rt6_record[:fraddr], 
                            :toaddr => rt6_record[:toaddr]} if not rt6_record[:fraddl].empty?
      end
      #names
      @names = []
      @names << {:fedirp => rt1_record[:fedirp], 
                 :fename => rt1_record[:fename], 
                 :fetype => rt1_record[:fetype], 
                 :fedirs => rt1_record[:fedirs]} if not rt1_record[:fename].empty?
      rt1_record.rt4_records.each do |rt4_record|
        rt4_record.rt5_records.each do |rt5_record|
          @names << {:fedirp => rt5_record[:fedirp], 
                     :fename => rt5_record[:fename], 
                     :fetype => rt5_record[:fetype], 
                     :fedirs => rt5_record[:fedirs]} if not rt5_record[:fename].empty?
        end
      end
      #cfcc
      @cfcc = rt1_record[:cfcc]
      #points
      @points = []
      @points << [ Helper.parse_long( rt1_record[:frlong] ), Helper.parse_lat( rt1_record[:frlat] ) ]
      rt1_record.rt2_records.sort! do |a,b| a[:rtsq] <=> b[:rtsq] end
      rt1_record.rt2_records.each do |rt2_record|
        (1..10).each do |i|
          long = Helper.parse_long( rt2_record[ ("long#{i}").intern ] )
          lat  = Helper.parse_lat( rt2_record[ ("lat#{i}").intern ] )
          if lat!=0 and long!=0 then
            @points << [long, lat]
          end
        end
      end
      @points << [ Helper.parse_long( rt1_record[:tolong] ), Helper.parse_lat( rt1_record[:tolat] ) ]
    end

    def line_wkt
      ret = "LINESTRING("
      ret << points.map do |long, lat| "#{long} #{lat}" end.join(",")
      ret << ")"
      return ret
    end
  end

  class Dataset
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

      #read record 1, 2, 4, 5, 6, I into arrays, or hashes if an key field name is provided
      rt1_records = RecordFile.read( @filename_base + ".RT1", RT1, :tlid )
      rt2_records = RecordFile.read( @filename_base + ".RT2", RT2 )
      rt4_records = RecordFile.read( @filename_base + ".RT4", RT4 )
      rt5_records = RecordFile.read( @filename_base + ".RT5", RT5, :feat )
      rt6_records = RecordFile.read( @filename_base + ".RT6", RT6 )
      rti_records = RecordFile.read( @filename_base + ".RTI", RTI )

      print "Joining tables\n"
      print "RT2 to RT1\n"
      #associate RT2s with their RT1
      rt2_records.each do |record|
        rt1_records[ record[:tlid] ].rt2_records << record
      end

      print "RT4 to RT1\n"
      #associate RT4s with their RT1
      rt4_records.each do |record|
        rt1_records[ record[:tlid] ].rt4_records << record
      end

      print "RT5 to RT4\n"
      #associate RT5s with their RT4
      rt4_records.each do |record|
        #the double hash call could be optimized
        record.rt5_records << rt5_records[ record[:feat1] ] if not record[:feat1].empty?
        record.rt5_records << rt5_records[ record[:feat2] ] if not record[:feat2].empty?
        record.rt5_records << rt5_records[ record[:feat3] ] if not record[:feat3].empty?
        record.rt5_records << rt5_records[ record[:feat4] ] if not record[:feat4].empty?
        record.rt5_records << rt5_records[ record[:feat5] ] if not record[:feat5].empty?
      end
      
      print "RT6 to RT1\n"
      #associate RT6s with their RT1
      rt6_records.each do |record|
        rt1_records[ record[:tlid] ].rt6_records << record
      end

      print "RTI to RT1\n"
      #associate RTI with its RT1
      rti_records.each do |record|
        rt1_records[ record[:tlid] ].rti_record = record
      end

      print "Parsing TIGER records into features...\n"
      i=0
      n=rt1_records.size
      rt1_records.each do |key, record|
        i += 1; if i%5000 == 0 then print sprintf("%.1f", (Float(i)/n)*100 ) + "%\n" end
        
        @features[ key ] = Feature.new( record )
      end

      true
    end

    def each_feature
      @features.each_pair do |tlid, feature|
        yield feature
      end
    end

  end

end
