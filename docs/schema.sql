-- The shape of the book after every migration.
-- Written by python -m holdtrim.tools.schema_dump at schema 12.

CREATE INDEX consignment_by_route ON consignment (origin, destination, ready_on);
CREATE INDEX dangerous_goods_by_awb ON dangerous_goods (awb, un_number);
CREATE INDEX hold_position_by_type ON hold_position (type_code, ordinal);
CREATE INDEX loadsheet_by_day ON loadsheet (issued_on);
CREATE INDEX plan_assignment_by_uld ON plan_assignment (uld);
CREATE INDEX sector_by_day ON sector (day, carrier, number);
CREATE INDEX sector_by_tail ON sector (registration, day);
CREATE INDEX station_by_name ON station (name);
CREATE INDEX tail_by_type ON tail (type_code);
CREATE INDEX uld_by_station ON uld (at_station, type_code);
CREATE INDEX uld_movement_by_station ON uld_movement (station, day);
CREATE INDEX uld_movement_by_uld ON uld_movement (uld, day);
CREATE TABLE aircraft_type ( code TEXT PRIMARY KEY, name TEXT NOT NULL, max_ramp INTEGER NOT NULL, max_takeoff INTEGER NOT NULL, max_landing INTEGER NOT NULL, max_zero_fuel INTEGER NOT NULL, reference_arm TEXT NOT NULL, lemac TEXT NOT NULL, mac_length TEXT NOT NULL, index_constant TEXT NOT NULL, index_reference TEXT NOT NULL, empty_weight INTEGER NOT NULL DEFAULT 0 );
CREATE TABLE consignment ( awb TEXT PRIMARY KEY, prefix TEXT NOT NULL, serial INTEGER NOT NULL, origin TEXT NOT NULL, destination TEXT NOT NULL, pieces INTEGER NOT NULL, gross_weight INTEGER NOT NULL, volume TEXT NOT NULL, commodity TEXT NOT NULL, ready_on TEXT NOT NULL, shipper TEXT NOT NULL DEFAULT '', consignee TEXT NOT NULL DEFAULT '', handling TEXT NOT NULL DEFAULT '' );
CREATE TABLE cumulative_limit ( type_code TEXT NOT NULL REFERENCES aircraft_type (code) ON DELETE CASCADE, label TEXT NOT NULL, max_weight INTEGER NOT NULL, positions TEXT NOT NULL, PRIMARY KEY (type_code, label) );
CREATE TABLE dangerous_goods ( id INTEGER PRIMARY KEY AUTOINCREMENT, awb TEXT NOT NULL, un_number INTEGER NOT NULL, proper_shipping_name TEXT NOT NULL, hazard_class TEXT NOT NULL, packages INTEGER NOT NULL, net_quantity TEXT NOT NULL, unit TEXT NOT NULL, packing_group TEXT NOT NULL DEFAULT '', packing_instruction TEXT NOT NULL DEFAULT '', subsidiary_risks TEXT NOT NULL DEFAULT '', cargo_aircraft_only INTEGER NOT NULL DEFAULT 0, transport_index TEXT NOT NULL DEFAULT '' );
CREATE TABLE envelope_point ( type_code TEXT NOT NULL REFERENCES aircraft_type (code) ON DELETE CASCADE, envelope TEXT NOT NULL, weight INTEGER NOT NULL, forward_index TEXT NOT NULL, aft_index TEXT NOT NULL, PRIMARY KEY (type_code, envelope, weight) );
CREATE TABLE fuel_point ( type_code TEXT NOT NULL REFERENCES aircraft_type (code) ON DELETE CASCADE, weight INTEGER NOT NULL, fuel_index TEXT NOT NULL, PRIMARY KEY (type_code, weight) );
CREATE TABLE hold_position ( type_code TEXT NOT NULL REFERENCES aircraft_type (code) ON DELETE CASCADE, code TEXT NOT NULL, ordinal INTEGER NOT NULL, compartment TEXT NOT NULL, arm TEXT NOT NULL, max_weight INTEGER NOT NULL, length TEXT NOT NULL, width TEXT NOT NULL, max_running_load INTEGER NOT NULL, max_area_load INTEGER NOT NULL, accepts TEXT NOT NULL DEFAULT '', PRIMARY KEY (type_code, code) );
CREATE TABLE load_plan ( flight_key TEXT PRIMARY KEY REFERENCES sector (key) ON DELETE CASCADE, edition INTEGER NOT NULL );
CREATE TABLE loadsheet ( flight_key TEXT NOT NULL REFERENCES sector (key) ON DELETE CASCADE, edition INTEGER NOT NULL, issued_on TEXT NOT NULL, prepared_by TEXT NOT NULL, payload INTEGER NOT NULL, zero_fuel_weight INTEGER NOT NULL, takeoff_weight INTEGER NOT NULL, landing_weight INTEGER NOT NULL, underload INTEGER NOT NULL, limited_by TEXT NOT NULL, takeoff_index TEXT NOT NULL, takeoff_percent_mac TEXT NOT NULL, trim_setting TEXT NOT NULL, lmc_weight INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (flight_key, edition) );
CREATE TABLE plan_assignment ( flight_key TEXT NOT NULL REFERENCES load_plan (flight_key) ON DELETE CASCADE, hold_position TEXT NOT NULL, ordinal INTEGER NOT NULL, weight INTEGER NOT NULL, uld TEXT NOT NULL DEFAULT '', destination TEXT NOT NULL DEFAULT '', PRIMARY KEY (flight_key, hold_position) );
CREATE TABLE schema_migration ( version INTEGER PRIMARY KEY, name TEXT NOT NULL );
CREATE TABLE sector ( key TEXT PRIMARY KEY, carrier TEXT NOT NULL, number INTEGER NOT NULL, suffix TEXT NOT NULL DEFAULT '', day TEXT NOT NULL, registration TEXT NOT NULL REFERENCES tail (registration), origin TEXT NOT NULL, destination TEXT NOT NULL, taxi_fuel INTEGER NOT NULL, trip_fuel INTEGER NOT NULL, takeoff_fuel INTEGER NOT NULL, crew INTEGER NOT NULL, freighter INTEGER NOT NULL, status TEXT NOT NULL );
CREATE TABLE station ( code TEXT PRIMARY KEY, name TEXT NOT NULL, elevation_feet INTEGER NOT NULL, handling_agent TEXT NOT NULL DEFAULT '', free_storage_days INTEGER NOT NULL DEFAULT 2 );
CREATE TABLE tail ( registration TEXT PRIMARY KEY, type_code TEXT NOT NULL REFERENCES aircraft_type (code), dry_operating_weight INTEGER NOT NULL, dry_operating_index TEXT NOT NULL, weighed_on TEXT NOT NULL, serial_number TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, weighing_valid_months INTEGER NOT NULL );
CREATE TABLE trim_point ( type_code TEXT NOT NULL REFERENCES aircraft_type (code) ON DELETE CASCADE, percent_mac TEXT NOT NULL, setting TEXT NOT NULL, PRIMARY KEY (type_code, percent_mac) );
CREATE TABLE uld ( code TEXT PRIMARY KEY, type_code TEXT NOT NULL, serial TEXT NOT NULL, owner TEXT NOT NULL, tare INTEGER NOT NULL, max_gross INTEGER NOT NULL, at_station TEXT NOT NULL DEFAULT '', condition TEXT NOT NULL, contour TEXT NOT NULL );
CREATE TABLE uld_movement ( id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, station TEXT NOT NULL, uld TEXT NOT NULL, type_code TEXT NOT NULL, serial TEXT NOT NULL, owner TEXT NOT NULL, direction TEXT NOT NULL, flight_key TEXT NOT NULL DEFAULT '', state TEXT NOT NULL, note TEXT NOT NULL DEFAULT '' );
