def get_coords(coords_dict: dict, city: str):
    if not city.lower() in coords_dict:
            return None
    else:
        return coords_dict[city]


