require 'Graph'
require 'test/unit'

g = Graph.new
g.add_vertex( "brandon" )

class TC_MyTest < Test::Unit::TestCase

  #def setup
  #end

  # def teardown
  # end

  def test_graph
    g = Graph.new
    assert_not_nil( g )
    v = g.add_vertex( "brandon" )
    assert_not_nil( g )
    vt = g.get_vertex( "brandon" )
    assert( v.equal? vt )
    w = g.add_vertex( "michelle" )
  end
 
  def test_vertex
  end 

  def test_edge
  end
end
