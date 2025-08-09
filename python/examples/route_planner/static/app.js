/**
 * Route Planner Interactive Map Application
 * Phase 3: Routing integration with visualization
 */

class RoutePlanner {
    constructor() {
        this.map = null;
        this.originMarker = null;
        this.destinationMarker = null;
        this.origin = null;
        this.destination = null;
        
        // Route visualization
        this.routeLayer = null;
        this.routeData = null;
        this.isCalculatingRoute = false;
        
        // Live dragging support with continuous updates
        this.pendingRouteRequest = null;
        this.isDragging = false;
        this.lastCalculatedOrigin = null;
        this.lastCalculatedDestination = null;
        this.minDragDistance = 0.0001; // ~11 meters
        this.liveUpdateRate = 100; // milliseconds (10 Hz)
        this.lastLiveUpdateTime = 0;
        this.continuousUpdateTimer = null;
        
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
        
        // Create new origin marker (green) - now draggable
        this.originMarker = L.marker([lat, lng], {
            icon: this.createIcon('green'),
            draggable: true
        }).addTo(this.map);
        
        // Add popup
        this.originMarker.bindPopup(`Origin<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`);
        
        // Add drag event handlers
        this.originMarker.on('dragstart', this.onOriginDragStart.bind(this));
        this.originMarker.on('drag', this.onOriginDrag.bind(this));
        this.originMarker.on('dragend', this.onOriginDragEnd.bind(this));
        
        this.updateUI();
        console.log('Origin set:', { lat, lng });
    }
    
    setDestination(lat, lng) {
        this.destination = { lat, lng };
        
        // Remove existing destination marker
        if (this.destinationMarker) {
            this.map.removeLayer(this.destinationMarker);
        }
        
        // Create new destination marker (red) - now draggable
        this.destinationMarker = L.marker([lat, lng], {
            icon: this.createIcon('red'),
            draggable: true
        }).addTo(this.map);
        
        // Add popup
        this.destinationMarker.bindPopup(`Destination<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`);
        
        // Add drag event handlers
        this.destinationMarker.on('dragstart', this.onDestinationDragStart.bind(this));
        this.destinationMarker.on('drag', this.onDestinationDrag.bind(this));
        this.destinationMarker.on('dragend', this.onDestinationDragEnd.bind(this));
        
        this.updateUI();
        console.log('Destination set:', { lat, lng });
        
        // Automatically start routing when both points are set
        this.calculateRoute();
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
    
    onOriginDragStart(event) {
        console.log('Origin drag started');
        
        // Set dragging state and start continuous updates
        this.isDragging = true;
        if (this.destination) {
            this.startContinuousUpdates();
        }
    }
    
    onOriginDrag(event) {
        const { lat, lng } = event.target.getLatLng();
        
        // Update internal coordinates
        this.origin = { lat, lng };
        
        // Trigger immediate live route calculation (throttled)
        if (this.destination) {
            this.calculateRouteLive();
        }
    }
    
    onOriginDragEnd(event) {
        const { lat, lng } = event.target.getLatLng();
        
        // Update internal coordinates
        this.origin = { lat, lng };
        
        // Update popup content
        this.originMarker.bindPopup(`Origin<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`);
        
        // Update UI and trigger routing if destination exists
        this.updateUI();
        console.log('Origin dragged to:', { lat, lng });
        
        // Stop continuous updates and do final route calculation
        this.stopContinuousUpdates();
        this.isDragging = false;
        
        if (this.destination) {
            this.calculateRoute(); // Final accurate calculation
        }
    }
    
    onDestinationDragStart(event) {
        console.log('Destination drag started');
        
        // Set dragging state and start continuous updates
        this.isDragging = true;
        if (this.origin) {
            this.startContinuousUpdates();
        }
    }
    
    onDestinationDrag(event) {
        const { lat, lng } = event.target.getLatLng();
        
        // Update internal coordinates
        this.destination = { lat, lng };
        
        // Trigger immediate live route calculation (throttled)
        if (this.origin) {
            this.calculateRouteLive();
        }
    }
    
    onDestinationDragEnd(event) {
        const { lat, lng } = event.target.getLatLng();
        
        // Update internal coordinates
        this.destination = { lat, lng };
        
        // Update popup content
        this.destinationMarker.bindPopup(`Destination<br>Lat: ${lat.toFixed(6)}<br>Lng: ${lng.toFixed(6)}`);
        
        // Update UI and trigger routing if origin exists
        this.updateUI();
        console.log('Destination dragged to:', { lat, lng });
        
        // Stop continuous updates and do final route calculation
        this.stopContinuousUpdates();
        this.isDragging = false;
        
        if (this.origin) {
            this.calculateRoute(); // Final accurate calculation
        }
    }
    
    hasPositionChanged(newOrigin, newDestination) {
        // Check if position changed enough to warrant a new calculation
        const originChanged = !this.lastCalculatedOrigin || 
            Math.abs(newOrigin.lat - this.lastCalculatedOrigin.lat) > this.minDragDistance ||
            Math.abs(newOrigin.lng - this.lastCalculatedOrigin.lng) > this.minDragDistance;
            
        const destinationChanged = !this.lastCalculatedDestination || 
            Math.abs(newDestination.lat - this.lastCalculatedDestination.lat) > this.minDragDistance ||
            Math.abs(newDestination.lng - this.lastCalculatedDestination.lng) > this.minDragDistance;
            
        return originChanged || destinationChanged;
    }
    
    calculateRouteLive() {
        const now = Date.now();
        const timeSinceLastUpdate = now - this.lastLiveUpdateTime;
        
        // Only update if enough time has passed (throttle)
        if (timeSinceLastUpdate >= this.liveUpdateRate) {
            this.lastLiveUpdateTime = now;
            
            if (this.origin && this.destination && this.hasPositionChanged(this.origin, this.destination)) {
                this.calculateRoute(true); // Pass true to indicate this is a live update
            }
        }
    }
    
    startContinuousUpdates() {
        // Start the continuous update timer if not already running
        if (!this.continuousUpdateTimer) {
            this.continuousUpdateTimer = setInterval(() => {
                if (this.isDragging && this.origin && this.destination) {
                    this.calculateRouteLive();
                }
            }, this.liveUpdateRate);
        }
    }
    
    stopContinuousUpdates() {
        // Stop the continuous update timer
        if (this.continuousUpdateTimer) {
            clearInterval(this.continuousUpdateTimer);
            this.continuousUpdateTimer = null;
        }
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
                if (this.origin && this.destination && !this.isCalculatingRoute) {
                    this.calculateRoute();
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
        
        // Clear route button
        const clearRouteButton = document.getElementById('clear-route');
        if (clearRouteButton) {
            clearRouteButton.addEventListener('click', () => {
                this.clearRoute();
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Only trigger shortcuts if not typing in an input field
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch (event.key.toLowerCase()) {
            case 'r':
                if (this.origin && this.destination && !this.isCalculatingRoute) {
                    event.preventDefault();
                    this.calculateRoute();
                }
                break;
            case 'c':
                event.preventDefault();
                this.clearPoints();
                break;
            case 'escape':
                event.preventDefault();
                this.clearRoute();
                break;
            }
        });
        
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
    
    async calculateRoute(isLiveUpdate = false) {
        if (!this.origin || !this.destination) {
            return;
        }
        
        // Don't allow overlapping calculations unless it's a live update
        if (!isLiveUpdate && this.isCalculatingRoute) {
            return;
        }
        
        // Cancel any pending request for live updates
        if (this.pendingRouteRequest) {
            this.pendingRouteRequest.abort();
        }
        
        // Create new AbortController for this request
        const abortController = new AbortController();
        this.pendingRouteRequest = abortController;
        
        // Update last calculated positions
        this.lastCalculatedOrigin = { ...this.origin };
        this.lastCalculatedDestination = { ...this.destination };
        
        if (!isLiveUpdate) {
            this.isCalculatingRoute = true;
            this.showRouteLoading();
        }
        
        try {
            const response = await fetch('/api/route', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    origin: this.origin,
                    destination: this.destination
                }),
                signal: abortController.signal
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const routeResult = await response.json();
            
            if (routeResult.properties && routeResult.properties.status === 'success') {
                this.routeData = routeResult;
                if (!isLiveUpdate) {
                    this.showRouteResult(routeResult);
                }
                this.visualizeRoute(routeResult, isLiveUpdate);
            } else {
                if (!isLiveUpdate) {
                    this.showRouteError(routeResult.properties || { error: 'No route found' });
                }
            }
            
        } catch (error) {
            // Don't show errors for aborted requests
            if (error.name === 'AbortError') {
                return;
            }
            
            console.error('Route calculation failed:', error);
            if (!isLiveUpdate) {
                this.showRouteError({
                    error: 'Route calculation failed',
                    error_details: `Network or server error: ${error.message}`,
                    debug_info: {
                        error_type: 'network_error',
                        original_message: error.message
                    }
                });
            }
        } finally {
            if (!isLiveUpdate) {
                this.isCalculatingRoute = false;
            }
            
            // Clear the pending request if it's the same one
            if (this.pendingRouteRequest === abortController) {
                this.pendingRouteRequest = null;
            }
        }
    }
    
    showRouteLoading() {
        const routeInfo = document.getElementById('route-info');
        const routeLoading = document.getElementById('route-loading');
        const routeResult = document.getElementById('route-result');
        const routeError = document.getElementById('route-error');
        
        if (routeInfo) routeInfo.classList.remove('hidden');
        if (routeLoading) routeLoading.classList.remove('hidden');
        if (routeResult) routeResult.classList.add('hidden');
        if (routeError) routeError.classList.add('hidden');
    }
    
    showRouteResult(routeData) {
        const routeLoading = document.getElementById('route-loading');
        const routeResult = document.getElementById('route-result');
        const routeError = document.getElementById('route-error');
        const clearRouteButton = document.getElementById('clear-route');
        
        if (routeLoading) routeLoading.classList.add('hidden');
        if (routeResult) routeResult.classList.remove('hidden');
        if (routeError) routeError.classList.add('hidden');
        if (clearRouteButton) clearRouteButton.classList.remove('hidden');
        
        // Update route information
        const statusElement = document.getElementById('route-status');
        const distanceElement = document.getElementById('route-distance');
        const costElement = document.getElementById('route-cost');
        const waypointsElement = document.getElementById('route-waypoints');
        const routingTimeElement = document.getElementById('routing-time');
        const geometryTimeElement = document.getElementById('geometry-time');
        const totalTimeElement = document.getElementById('total-time');
        
        if (statusElement) statusElement.textContent = 'Route Found';
        if (distanceElement) {
            const distance = routeData.properties?.total_distance || 0;
            distanceElement.textContent = `${(distance / 1000).toFixed(2)} km`;
        }
        if (costElement) {
            const cost = routeData.properties?.total_cost || 0;
            costElement.textContent = `${cost.toFixed(1)} units`;
        }
        if (waypointsElement) {
            const waypoints = routeData.properties?.waypoint_count || 0;
            waypointsElement.textContent = waypoints;
        }
        
        // Update timing information
        if (routingTimeElement && routeData.properties?.timing) {
            const routingTime = routeData.properties.timing.routing_time_ms || 0;
            routingTimeElement.textContent = `${routingTime.toFixed(1)} ms`;
        }
        if (geometryTimeElement && routeData.properties?.timing) {
            const geometryTime = routeData.properties.timing.geometry_time_ms || 0;
            geometryTimeElement.textContent = `${geometryTime.toFixed(1)} ms`;
        }
        if (totalTimeElement && routeData.properties?.timing) {
            const totalTime = routeData.properties.timing.total_time_ms || 0;
            totalTimeElement.textContent = `${totalTime.toFixed(1)} ms`;
        }
    }
    
    showRouteError(errorData) {
        const routeLoading = document.getElementById('route-loading');
        const routeResult = document.getElementById('route-result');
        const routeError = document.getElementById('route-error');
        const routeErrorText = document.getElementById('route-error-text');
        
        if (routeLoading) routeLoading.classList.add('hidden');
        if (routeResult) routeResult.classList.add('hidden');
        if (routeError) routeError.classList.remove('hidden');
        
        if (routeErrorText && errorData) {
            let errorHtml = `<strong>${errorData.error || 'Route Error'}</strong>`;
            
            // Add error details if available
            if (errorData.error_details) {
                errorHtml += `<br><small style="color: #666;">${errorData.error_details}</small>`;
            }
            
            // Log debug info to console for troubleshooting
            if (errorData.debug_info) {
                console.log('Route Error Debug Info:', errorData.debug_info);
                
                // Show some key debug info in the UI
                const debugInfo = errorData.debug_info;
                if (debugInfo.search_radius_m || debugInfo.approximate_distance_km) {
                    errorHtml += '<br><small style="color: #888;">Debug: ';
                    if (debugInfo.search_radius_m) {
                        errorHtml += `Search radius: ${debugInfo.search_radius_m}m `;
                    }
                    if (debugInfo.approximate_distance_km) {
                        errorHtml += `Distance: ${debugInfo.approximate_distance_km}km`;
                    }
                    errorHtml += '</small>';
                }
            }
            
            routeErrorText.innerHTML = errorHtml;
        }
    }
    
    visualizeRoute(routeData, isLiveUpdate = false) {
        // Clear existing route
        this.clearRouteVisualization();
        
        if (!routeData.features || routeData.features.length === 0) {
            return;
        }
        
        // Create a layer group for the route
        this.routeLayer = L.layerGroup();
        
        // Determine opacity based on update type
        const lineOpacity = isLiveUpdate ? 0.5 : 0.8;
        const waypointOpacity = isLiveUpdate ? 0.6 : 1.0;
        const waypointFillOpacity = isLiveUpdate ? 0.4 : 0.8;
        
        // Add each feature to the route layer
        routeData.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                const coordinates = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                
                const routeLine = L.polyline(coordinates, {
                    color: '#e74c3c',
                    weight: 4,
                    opacity: lineOpacity,
                    className: isLiveUpdate ? 'route-line route-line-live' : 'route-line'
                });
                
                this.routeLayer.addLayer(routeLine);
                
                // Add waypoint markers if available (hide during live updates for cleaner look)
                if (feature.properties.waypoints && !isLiveUpdate) {
                    feature.properties.waypoints.forEach((waypoint, index) => {
                        const waypointMarker = L.circleMarker([waypoint.position[1], waypoint.position[0]], {
                            radius: 6,
                            fillColor: '#e67e22',
                            color: '#d35400',
                            weight: 2,
                            opacity: waypointOpacity,
                            fillOpacity: waypointFillOpacity,
                            className: 'route-waypoint'
                        });
                        
                        waypointMarker.bindPopup(`
                            <strong>Waypoint ${index + 1}</strong><br>
                            ${waypoint.instruction}<br>
                            Cost: ${waypoint.cost.toFixed(2)}
                        `);
                        
                        this.routeLayer.addLayer(waypointMarker);
                    });
                }
            }
        });
        
        // Add the route layer to the map
        this.routeLayer.addTo(this.map);
        
        // Only fit bounds for final routes, not live updates
        if (!isLiveUpdate && this.routeLayer.getBounds && this.routeLayer.getBounds().isValid()) {
            this.map.fitBounds(this.routeLayer.getBounds(), { padding: [20, 20] });
        }
    }
    
    clearPoints() {
        // Clear route first
        this.clearRoute();
        
        // Clear markers
        if (this.originMarker) {
            this.map.removeLayer(this.originMarker);
            this.originMarker = null;
        }
        if (this.destinationMarker) {
            this.map.removeLayer(this.destinationMarker);
            this.destinationMarker = null;
        }
        
        // Clear point data
        this.origin = null;
        this.destination = null;
        
        // Update UI
        this.updateUI();
    }
    
    clearRoute() {
        this.clearRouteVisualization();
        this.routeData = null;
        
        // Hide route info
        const routeInfo = document.getElementById('route-info');
        const clearRouteButton = document.getElementById('clear-route');
        
        if (routeInfo) routeInfo.classList.add('hidden');
        if (clearRouteButton) clearRouteButton.classList.add('hidden');
    }
    
    clearRouteVisualization() {
        if (this.routeLayer) {
            this.map.removeLayer(this.routeLayer);
            this.routeLayer = null;
        }
    }
}

// Initialize the Route Planner when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.routePlanner = new RoutePlanner();
});