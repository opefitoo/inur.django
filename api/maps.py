import requests

from invoices.distancematrix import DistanceMatrix


def create_distance_matrix(location_dict, api_key):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    distance_matrix = {}
    duration_matrix = {}
    addresses = [location_dict[custom_id] for custom_id in location_dict.keys()]

    for origin in addresses:
        distance_matrix[origin] = {}
        duration_matrix[origin] = {}
        for destination in addresses:
            if origin == destination:
                # Distance to the same location is zero
                distance_matrix[origin][destination] = 0
            else:
                params = {
                    'origins': origin,
                    'destinations': destination,
                    'key': api_key,
                    'mode': 'driving',
                    'language': 'en-EN',
                    'units': 'metric'
                }
                response = requests.get(url, params=params)
                result = response.json()
                if result['status'] != 'OK':
                    raise Exception(result['error_message'])
                distance = result['rows'][0]['elements'][0]['distance']['text']
                duration = result['rows'][0]['elements'][0]['duration']['text']
                # convert distance to integer knowing that the distance is in km and looks like that '35.0 km'
                distance = int(float(distance.split(' ')[0]))
                # convert duration to integer
                duration = int(duration.split(' ')[0])
                distance_matrix[origin][destination] = distance
                duration_matrix[origin][destination] = duration
                # retrieve the key from the dictionary using the value origin or destination
                origin_patient = list(location_dict.keys())[list(location_dict.values()).index(origin)]
                destination_patient = list(location_dict.keys())[list(location_dict.values()).index(destination)]
                print(origin_patient, destination_patient, distance, duration)
                dmatrix = DistanceMatrix.objects.create(
                    patient_origin=origin_patient,
                    patient_destination=destination_patient,
                    distance_in_km=distance,
                    duration_in_mn=duration
                )
                dmatrix.save()

    return distance_matrix

# Example usage
#locations = ['XX', 'YY', 'ZZ']
# matrix = create_distance_matrix(locations, api_key)
