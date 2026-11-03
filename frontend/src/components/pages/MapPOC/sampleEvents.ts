// Events don't store coordinates yet, so this POC uses hardcoded sample data.
// The first five mirror backend/python/seeds/events.csv; the rest add spread
// across the GTA. Shape is a camelCase subset of the backend EventRead model.

export type MapEvent = {
  id: string;
  name: string;
  location: string;
  eventStatus: string;
  startDatetime: string;
  endDatetime: string;
  lat: number;
  lng: number;
};

export const TORONTO_CENTER = { lat: 43.6532, lng: -79.3832 };

export const SAMPLE_EVENTS: MapEvent[] = [
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000001",
    name: "Bluffers Park Beach Cleanup",
    location: "Bluffers Park, Scarborough",
    eventStatus: "completed",
    startDatetime: "2026-05-10T09:00:00",
    endDatetime: "2026-05-10T12:00:00",
    lat: 43.7064,
    lng: -79.2307,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000002",
    name: "Rouge Valley Tree Planting",
    location: "Rouge National Urban Park, Toronto",
    eventStatus: "completed",
    startDatetime: "2026-04-20T08:30:00",
    endDatetime: "2026-04-20T12:30:00",
    lat: 43.8115,
    lng: -79.1773,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000003",
    name: "Woodbine Beach Cleanup",
    location: "Woodbine Beach, Toronto",
    eventStatus: "published",
    startDatetime: "2026-08-15T09:00:00",
    endDatetime: "2026-08-15T12:00:00",
    lat: 43.6628,
    lng: -79.3068,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000004",
    name: "Composting 101 Workshop",
    location: "Toronto Reference Library, Toronto",
    eventStatus: "published",
    startDatetime: "2026-09-05T18:00:00",
    endDatetime: "2026-09-05T19:30:00",
    lat: 43.6717,
    lng: -79.3867,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000005",
    name: "High Park Tree Planting",
    location: "High Park, Toronto",
    eventStatus: "published",
    startDatetime: "2026-08-30T09:00:00",
    endDatetime: "2026-08-30T13:00:00",
    lat: 43.6465,
    lng: -79.4637,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000006",
    name: "Brick Works Invasive Species Pull",
    location: "Evergreen Brick Works, Toronto",
    eventStatus: "published",
    startDatetime: "2026-11-07T10:00:00",
    endDatetime: "2026-11-07T13:00:00",
    lat: 43.6846,
    lng: -79.3653,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000007",
    name: "Tommy Thompson Park Shoreline Cleanup",
    location: "Tommy Thompson Park, Toronto",
    eventStatus: "published",
    startDatetime: "2026-11-14T09:30:00",
    endDatetime: "2026-11-14T12:30:00",
    lat: 43.629,
    lng: -79.3305,
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-000000000008",
    name: "Humber Bay Pollinator Garden Planting",
    location: "Humber Bay Park East, Etobicoke",
    eventStatus: "published",
    startDatetime: "2026-11-21T10:00:00",
    endDatetime: "2026-11-21T12:00:00",
    lat: 43.6232,
    lng: -79.4785,
  },
];
