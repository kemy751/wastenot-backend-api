from app.models.product import ElectronicType

class AdvancedGreenEngine:
    # 1. Exhaustive baseline metrics mapped exactly to your Enum keys
    # Format: {"carbon": manufacturing_co2e_kg, "weight": average_physical_weight_kg}
    BASELINES = {
        # Core Mobile & Computing
        ElectronicType.SMARTPHONE: {"carbon": 65.0, "weight": 0.2},
        ElectronicType.LAPTOP: {"carbon": 220.0, "weight": 1.8},
        ElectronicType.TABLET: {"carbon": 90.0, "weight": 0.5},
        ElectronicType.DESKTOP_PC: {"carbon": 300.0, "weight": 8.0},
        ElectronicType.MONITOR: {"carbon": 180.0, "weight": 4.5},
        
        # Audio & Wearables
        ElectronicType.AUDIO_HEADPHONES: {"carbon": 25.0, "weight": 0.25},
        ElectronicType.SPEAKERS_SUBWOOFERS: {"carbon": 85.0, "weight": 6.0},
        ElectronicType.SMART_WATCH: {"carbon": 38.0, "weight": 0.05},
        ElectronicType.FITNESS_TRACKER: {"carbon": 22.0, "weight": 0.03},
        
        # Entertainment & Gaming
        ElectronicType.GAMING_CONSOLE: {"carbon": 160.0, "weight": 3.2},
        ElectronicType.TELEVISION: {"carbon": 320.0, "weight": 15.0},
        ElectronicType.STREAMING_DEVICE: {"carbon": 18.0, "weight": 0.1},
        ElectronicType.PROJECTOR: {"carbon": 140.0, "weight": 2.8},
        
        # Automotive Electronics
        ElectronicType.CAR_AUDIO_NAVIGATION: {"carbon": 75.0, "weight": 1.5},
        
        # Cameras & Photography
        ElectronicType.CAMERA_BODY: {"carbon": 110.0, "weight": 0.6},
        ElectronicType.CAMERA_LENS: {"carbon": 60.0, "weight": 0.4},
        ElectronicType.DRONE: {"carbon": 130.0, "weight": 0.9},
        
        # Computer Parts & Components
        ElectronicType.GRAPHICS_CARD: {"carbon": 110.0, "weight": 1.1},
        ElectronicType.PROCESSOR_CPU: {"carbon": 45.0, "weight": 0.05},
        ElectronicType.MOTHERBOARD: {"carbon": 55.0, "weight": 0.7},
        ElectronicType.RAM_MEMORY: {"carbon": 15.0, "weight": 0.03},
        ElectronicType.STORAGE_SSD_HDD: {"carbon": 28.0, "weight": 0.15},
        ElectronicType.POWER_SUPPLY: {"carbon": 45.0, "weight": 2.0},
        
        # Networking Equipment
        ElectronicType.ROUTER_MODEM: {"carbon": 35.0, "weight": 0.4},
        ElectronicType.NETWORK_SWITCH: {"carbon": 65.0, "weight": 1.2},
        
        # Smart Home & Peripherals
        ElectronicType.SMART_HOME_HUB: {"carbon": 25.0, "weight": 0.2},
        ElectronicType.SECURITY_CAMERA: {"carbon": 40.0, "weight": 0.3},
        ElectronicType.PRINTER_SCANNER: {"carbon": 120.0, "weight": 7.0},
        ElectronicType.KEYBOARD_MOUSE: {"carbon": 18.0, "weight": 0.5},
        
        # Electronic Home Appliances & Tools
        ElectronicType.HOME_APPLIANCES_TOOLS: {"carbon": 180.0, "weight": 5.5},
        
        # Fallback Safety Default
        ElectronicType.OTHER: {"carbon": 40.0, "weight": 1.0}
    }
    
    DISPLACEMENT_FACTOR = 0.7 

    @classmethod
    def calculate_product_impact(cls, product) -> float:
        """
        Dynamically processes product parameters against exact enum taxonomy definitions.
        """
        # Safely extract baseline profile values
        spec = cls.BASELINES.get(product.electronic_type, cls.BASELINES[ElectronicType.OTHER])
        base_carbon = spec["carbon"]
        base_weight = spec["weight"]
        
        # Modifier 1: Relative Structural Mass Tuning
        weight_modifier = 1.0
        if product.weight_kg and product.weight_kg > 0:
            # Multiplier scales dynamically based on physical weight delta
            # Hard-capped between 0.5x and 2.5x to filter crazy outliers safely
            weight_modifier = max(0.5, min(2.5, product.weight_kg / base_weight))

        # Modifier 2: Lithium Processing Surcharge
        battery_tax = 0.0
        if product.has_lithium_battery:
            # Heavy battery cells (Laptops, Tablets, Drones, handheld tools)
            if product.electronic_type in [
                ElectronicType.LAPTOP, 
                ElectronicType.TABLET, 
                ElectronicType.DRONE, 
                ElectronicType.HOME_APPLIANCES_TOOLS
            ]:
                battery_tax = 25.0
            # Small structural battery cells (Phones, Wearables)
            else:
                battery_tax = 10.0

        # Modifier 3: Grid Modernization and Efficiency Era Adjustment
        era_modifier = 1.0
        if product.release_year:
            if product.release_year < 2015:
                era_modifier = 1.15  # Older equipment required historically heavier power grids
            elif product.release_year >= 2024:
                era_modifier = 0.90  # Modern plants feature tighter supply chain optimization

        # --- COMBINE FORMULA ATTRIBUTES ---
        embodied_co2e = (base_carbon * weight_modifier * era_modifier) + battery_tax
        
        # Factor in resale displacement rate
        final_offset_kg = embodied_co2e * cls.DISPLACEMENT_FACTOR
        
        return round(final_offset_kg, 1)

    @classmethod
    def get_ui_translations(cls, kg_co2e: float) -> dict:
        return {
            "kg_co2_saved": kg_co2e,
            "car_miles_prevented": round(kg_co2e * 2.5, 1),
            "tree_days_saved": round(kg_co2e * 22.1, 1),
            "smartphone_charges_equivalent": round(kg_co2e * 121.5)
        }