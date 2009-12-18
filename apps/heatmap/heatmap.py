from servable import Servable

class Heatmap(Servable):
    def index(self):
        return open("heatmap.html").read()
    index.mime = "text/html"
        
if __name__=='__main__':
    hh = Heatmap()
    hh.run_test_server()