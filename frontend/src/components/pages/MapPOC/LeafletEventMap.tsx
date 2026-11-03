import "leaflet/dist/leaflet.css";
import L from "leaflet";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import React, { useEffect, useRef } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";

import EventPopupContent from "./EventPopupContent";
import { EventMapProps } from "./types";

// Leaflet's default icon resolves its image paths from CSS, which breaks
// under webpack, so build the icon from the bundled image imports instead.
const markerIconConfig = new L.Icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const SELECTED_ZOOM = 14;

// Pans to the selected event and opens its popup. Lives inside MapContainer
// because useMap() only works there.
const SelectedEventSync = ({
  events,
  selectedEventId,
  markerRefs,
}: Pick<EventMapProps, "events" | "selectedEventId"> & {
  markerRefs: React.MutableRefObject<Record<string, L.Marker | null>>;
}): null => {
  const map = useMap();

  useEffect(() => {
    const event = events.find((e) => e.id === selectedEventId);
    if (!event) {
      map.closePopup();
      return;
    }
    map.flyTo([event.lat, event.lng], Math.max(map.getZoom(), SELECTED_ZOOM));
    markerRefs.current[event.id]?.openPopup();
  }, [events, selectedEventId, map, markerRefs]);

  return null;
};

const LeafletEventMap = ({
  events,
  selectedEventId,
  onSelectEvent,
}: EventMapProps): React.ReactElement => {
  const markerRefs = useRef<Record<string, L.Marker | null>>({});

  // Opening one popup closes the previous one; only clear the selection when
  // the closed popup belongs to the currently selected event.
  const selectedEventIdRef = useRef(selectedEventId);
  selectedEventIdRef.current = selectedEventId;

  const bounds = L.latLngBounds(events.map((e) => [e.lat, e.lng]));

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ padding: [40, 40] }}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {events.map((event) => (
        <Marker
          key={event.id}
          position={[event.lat, event.lng]}
          icon={markerIconConfig}
          title={event.name}
          alt={event.name}
          ref={(marker) => {
            markerRefs.current[event.id] = marker;
          }}
          eventHandlers={{
            click: () => onSelectEvent(event.id),
            popupclose: () => {
              if (selectedEventIdRef.current === event.id) onSelectEvent(null);
            },
          }}
        >
          <Popup>
            <EventPopupContent event={event} />
          </Popup>
        </Marker>
      ))}
      <SelectedEventSync
        events={events}
        selectedEventId={selectedEventId}
        markerRefs={markerRefs}
      />
    </MapContainer>
  );
};

export default LeafletEventMap;
