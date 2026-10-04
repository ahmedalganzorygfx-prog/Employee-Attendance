import math
import secrets

def distance_meters(lat1, lon1, lat2, lon2):
    """
    حساب المسافة الجغرافية بين نقطتين بالمتر باستخدام معادلة Haversine
    """
    R = 6371000.0  # نصف قطر الكرة الأرضية بالمتر
    
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def valid_coords(lat, lon):
    """
    التحقق من صحة الإحداثيات الجغرافية المأخوذة من الـ GPS
    """
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (ValueError, TypeError):
        return False

def token():
    """
    توليد رمز أمان عشوائي وشفري لإنشاء الـ QR Code الخاص بالفرع
    """
    return secrets.token_hex(16)
