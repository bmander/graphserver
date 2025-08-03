/**
 * Route Planner Interactive Map Application
 * Phase 2: Map interface with click-to-set points
 */

class RoutePlanner {
    constructor() {
        this.map = null;
        this.originMarker = null;
        this.destinationMarker = null;
        this.origin = null;
        this.destination = null;
        
        // Initialize the application
        this.initializeApp();
    }
    
    async initializeApp() {
        try {
            await this.initializeMap();
            this.setupEventHandlers();
            await this.updateServerStatus();
            
            console.log('Route Planner initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Route Planner:', error);
            this.showError('Failed to initialize map. Please refresh the page.');
        }
    }
    
    async initializeMap() {
        try {
            // Get OSM bounds from server
            const bounds = await this.getOSMBounds();
            
            // Initialize Leaflet map
            this.map = L.map('map').fitBounds([
                [bounds.south, bounds.west],
                [bounds.north, bounds.east]
            ]);
            
            // Add OpenStreetMap tile layer
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
                maxZoom: 19
            }).addTo(this.map);
            
            // Add click handler
            this.map.on('click', this.onMapClick.bind(this));
            
            console.log('Map initialized with bounds:', bounds);
        } catch (error) {
            console.error('Map initialization failed:', error);
            throw error;
        }
    }
    
    onMapClick(event) {
        const { lat, lng } = event.latlng;
        
        if (!this.origin) {
            this.setOrigin(lat, lng);
        } else if (!this.destination) {
            this.setDestination(lat, lng);
        } else {
            // Reset and set new origin
            this.clearPoints();
            this.setOrigin(lat, lng);
        }
    }
    
    setOrigin(lat, lng) {
        this.origin = { lat, lng };
        
        // Remove existing origin marker
        if (this.originMarker) {
            this.map.removeLayer(this.originMarker);
        }
        
        // Create new origin marker (green)
        this.originMarker = L.marker([lat, lng], {
            icon: this.createIcon('green')
        }).addTo(this.map);
        
        // Add popup
        this.originMarker.bindPopup(`Origin<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`);
        
        this.updateUI();
        console.log('Origin set:', { lat, lng });
    }
    
    setDestination(lat, lng) {
        this.destination = { lat, lng };
        
        // Remove existing destination marker
        if (this.destinationMarker) {
            this.map.removeLayer(this.destinationMarker);
        }
        
        // Create new destination marker (red)
        this.destinationMarker = L.marker([lat, lng], {
            icon: this.createIcon('red')
        }).addTo(this.map);
        
        // Add popup
        this.destinationMarker.bindPopup(`Destination<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`);
        
        this.updateUI();
        console.log('Destination set:', { lat, lng });
    }
    
    clearPoints() {
        // Clear origin
        if (this.originMarker) {
            this.map.removeLayer(this.originMarker);
            this.originMarker = null;
        }
        this.origin = null;
        
        // Clear destination
        if (this.destinationMarker) {
            this.map.removeLayer(this.destinationMarker);
            this.destinationMarker = null;
        }
        this.destination = null;
        
        this.updateUI();
        console.log('Points cleared');
    }
    
    createIcon(color) {
        const colorMap = {
            'green': '#2ecc71',
            'red': '#e74c3c'
        };
        
        return L.divIcon({
            className: 'custom-marker',
            html: `<div style="
                width: 20px;
                height: 20px;
                background-color: ${colorMap[color]};
                border: 3px solid white;
                border-radius: 50%;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            "></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
    }
    
    async getOSMBounds() {
        try {
            const response = await fetch('/api/bounds');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get OSM bounds:', error);
            // Return default bounds (Seattle area)
            return {
                south: 47.6,
                west: -122.4,
                north: 47.7,
                east: -122.2
            };
        }
    }
    
    updateUI() {
        // Update point status indicators
        const originStatus = document.getElementById('origin-status');
        const destinationStatus = document.getElementById('destination-status');
        const calculateButton = document.getElementById('calculate-route');
        
        if (originStatus) {
            const label = originStatus.querySelector('.point-label');
            if (this.origin) {
                label.textContent = `Origin: ${this.origin.lat.toFixed(4)}, ${this.origin.lng.toFixed(4)}`;
                originStatus.classList.add('point-set');
            } else {
                label.textContent = 'Origin: Click map to set';
                originStatus.classList.remove('point-set');
            }
        }
        
        if (destinationStatus) {
            const label = destinationStatus.querySelector('.point-label');
            if (this.destination) {
                label.textContent = `Destination: ${this.destination.lat.toFixed(4)}, ${this.destination.lng.toFixed(4)}`;
                destinationStatus.classList.add('point-set');
            } else {
                if (this.origin) {
                    label.textContent = 'Destination: Click map to set';
                } else {
                    label.textContent = 'Destination: Set origin first';
                }
                destinationStatus.classList.remove('point-set');
            }
        }
        
        // Enable calculate button only when both points are set
        if (calculateButton) {
            calculateButton.disabled = !(this.origin && this.destination);
        }
    }
    
    async updateServerStatus() {
        const statusElement = document.getElementById('status');
        const statusText = statusElement?.querySelector('.status-text');
        const connectionStatus = document.getElementById('connection-status');
        const osmFile = document.getElementById('osm-file');
        const gtfsFiles = document.getElementById('gtfs-files');
        
        try {
            const response = await fetch('/api/status');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update main status indicator
            if (statusElement && statusText) {
                statusElement.className = 'status-indicator status-ok';
                statusText.textContent = '✓ Connected';
            }
            
            // Update server info panel
            if (connectionStatus) {
                connectionStatus.textContent = 'Connected';
                connectionStatus.className = 'status-connected';
            }
            
            // Display OSM file info
            if (osmFile && data.config?.osm_file) {
                const fileName = data.config.osm_file.split('/').pop();
                osmFile.textContent = fileName;
            } else if (osmFile) {
                osmFile.textContent = 'Not specified';
            }
            
            // Display GTFS files info
            if (gtfsFiles) {
                if (data.config?.gtfs_files?.length > 0) {
                    const fileNames = data.config.gtfs_files.map(f => f.split('/').pop());
                    gtfsFiles.textContent = fileNames.join(', ');
                } else {
                    gtfsFiles.textContent = 'None';
                }
            }
            
        } catch (error) {
            console.error('Server connection failed:', error);
            
            // Update main status indicator
            if (statusElement && statusText) {
                statusElement.className = 'status-indicator status-error';
                statusText.textContent = '✗ Connection failed';
            }
            
            // Update server info panel
            if (connectionStatus) {
                connectionStatus.textContent = 'Failed';
                connectionStatus.className = 'status-failed';
            }
            if (osmFile) osmFile.textContent = 'Unknown';
            if (gtfsFiles) gtfsFiles.textContent = 'Unknown';
        }
    }
    
    setupEventHandlers() {
        // Calculate route button
        const calculateButton = document.getElementById('calculate-route');
        if (calculateButton) {
            calculateButton.addEventListener('click', () => {
                if (this.origin && this.destination) {
                    alert('Route calculation will be implemented in Phase 3!\n\n' +
                          `Origin: ${this.origin.lat.toFixed(6)}, ${this.origin.lng.toFixed(6)}\n` +
                          `Destination: ${this.destination.lat.toFixed(6)}, ${this.destination.lng.toFixed(6)}`);
                }
            });
        }
        
        // Clear points button
        const clearButton = document.getElementById('clear-points');
        if (clearButton) {
            clearButton.addEventListener('click', () => {
                this.clearPoints();
            });
        }
        
        // Refresh status every 30 seconds
        setInterval(() => {
            this.updateServerStatus();
        }, 30000);
    }
    
    showError(message) {
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    background: #f8f9fa;
                    color: #666;
                    text-align: center;
                    padding: 2rem;
                ">
                    <div>
                        <h3>Map Error</h3>
                        <p>${message}</p>
                    </div>
                </div>
            `;
        }
    }
}

// Initialize the Route Planner when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.routePlanner = new RoutePlanner();
});