import logging
import uuid
from typing import Union, List, Optional
from app.extensions import db
from app.models import Product, Listing, ListingInterest, User  # Fixed: Imported User model

# Initialize module-specific logger
logger = logging.getLogger(__name__)

# Type alias for cleaner, safer flexible primary key handling
IdType = Union[uuid.UUID, str]

class ProductService:
    @staticmethod
    def create(data: dict) -> Product:
        logger.info(f"Attempting to create product: {data.get('brand')} {data.get('model_name')}")
        try:
            product = Product(**data)
            db.session.add(product)
            db.session.commit()
            logger.info(f"Successfully created product with ID: {product.id}")
            return product
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create product. Error: {str(e)}")
            raise e

    @staticmethod
    def get_by_id(product_id: IdType) -> Optional[Product]:
        logger.info(f"Fetching product with ID: {product_id}")
        # Fixed: Converted to db.session.get() to comply with modern SQLAlchemy standards
        return db.session.get(Product, product_id)

    @staticmethod
    def get_all() -> List[Product]:
        logger.info("Fetching all products")
        return Product.query.all()

    @staticmethod
    def update(product_id: IdType, data: dict) -> Optional[Product]:
        logger.info(f"Attempting to update product ID {product_id} with data: {data}")
        product = ProductService.get_by_id(product_id)
        if not product:
            logger.warning(f"Product with ID {product_id} not found for update")
            return None
        
        try:
            for key, value in data.items():
                setattr(product, key, value)
            db.session.commit()
            logger.info(f"Successfully updated product ID: {product_id}")
            return product
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update product ID {product_id}. Error: {str(e)}")
            raise e

    @staticmethod
    def delete(product_id: IdType) -> bool:
        logger.info(f"Attempting to delete product ID: {product_id}")
        product = ProductService.get_by_id(product_id)
        if not product:
            logger.warning(f"Product with ID {product_id} not found for deletion")
            return False
            
        try:
            db.session.delete(product)
            db.session.commit()
            logger.info(f"Successfully deleted product ID: {product_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete product ID {product_id}. Error: {str(e)}")
            raise e


class ListingService:
    @staticmethod
    def create(data: dict) -> Listing:
        logger.info(f"Attempting to create listing for product ID {data.get('product_id')} by seller ID {data.get('seller_id')}")
        try:
            listing = Listing(**data)
            db.session.add(listing)
            db.session.commit()
            logger.info(f"Successfully created listing with ID: {listing.id}")
            return listing
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create listing. Error: {str(e)}")
            raise e

    @staticmethod
    def get_by_id(listing_id: IdType) -> Optional[Listing]:
        logger.info(f"Fetching listing with ID: {listing_id}")
        return db.session.get(Listing, listing_id)

    @staticmethod
    def get_all() -> List[Listing]:
        logger.info("Fetching all active listings")
        return Listing.query.order_by(Listing.created_at.desc()).all()

    @staticmethod
    def update(listing_id: IdType, data: dict) -> Optional[Listing]:
        logger.info(f"Attempting to update listing ID {listing_id} with data: {data}")
        listing = ListingService.get_by_id(listing_id)
        if not listing:
            logger.warning(f"Listing with ID {listing_id} not found for update")
            return None
            
        try:
            for key, value in data.items():
                setattr(listing, key, value)
            db.session.commit()
            logger.info(f"Successfully updated listing ID: {listing_id}")
            return listing
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update listing ID {listing_id}. Error: {str(e)}")
            raise e

    @staticmethod
    def delete(listing_id: IdType) -> bool:
        logger.info(f"Attempting to delete listing ID: {listing_id}")
        listing = ListingService.get_by_id(listing_id)
        if not listing:
            logger.warning(f"Listing with ID {listing_id} not found for deletion")
            return False
            
        try:
            db.session.delete(listing)
            db.session.commit()
            logger.info(f"Successfully deleted listing ID: {listing_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete listing ID {listing_id}. Error: {str(e)}")
            raise e


class ListingInterestService:
    @staticmethod
    def create(data: dict) -> ListingInterest:
        logger.info(f"Buyer ID {data.get('buyer_id')} expressing interest in listing ID {data.get('listing_id')}")
        try:
            interest = ListingInterest(**data)
            db.session.add(interest)
            db.session.commit()
            
            # Context Hydration (Using modern db.session.get)
            listing = db.session.get(Listing, interest.listing_id)
            seller = db.session.get(User, listing.seller_id) if listing else None
            
            # Fixed: Combined brand and model name since title doesn't exist on Listing table
            if listing and listing.product:
                interest.listing_title = f"{listing.product.brand} {listing.product.model_name}"
            else:
                interest.listing_title = "Unknown Item"
                
            interest.seller_phone = seller.phone if seller else ""
            interest.seller_name = seller.name if seller else "Seller"
        
            logger.info(f"Successfully created interest tracking entry ID: {interest.id}")
            return interest
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record interest entry. Error: {str(e)}")
            raise e

    @staticmethod
    def get_by_id(interest_id: IdType) -> Optional[ListingInterest]:
        logger.info(f"Fetching interest entry with ID: {interest_id}")
        return db.session.get(ListingInterest, interest_id)

    @staticmethod
    def get_all_for_listing(listing_id: IdType) -> List[ListingInterest]:
        logger.info(f"Fetching all active interest expressions/waitlist for listing ID: {listing_id}")
        return ListingInterest.query.filter_by(listing_id=listing_id)\
                                    .order_by(ListingInterest.created_at.asc()).all()

    @staticmethod
    def update(interest_id: IdType, data: dict) -> Optional[ListingInterest]:
        logger.info(f"Updating interest entry ID {interest_id} status/data: {data}")
        interest = ListingInterestService.get_by_id(interest_id)
        if not interest:
            logger.warning(f"Interest record with ID {interest_id} not found for update")
            return None
            
        try:
            for key, value in data.items():
                setattr(interest, key, value)
            db.session.commit()
            logger.info(f"Successfully updated interest entry ID: {interest_id}")
            return interest
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update interest record {interest_id}. Error: {str(e)}")
            raise e

    @staticmethod
    def delete(interest_id: IdType) -> bool:
        logger.info(f"Attempting to remove interest entry ID: {interest_id}")
        interest = ListingInterestService.get_by_id(interest_id)
        if not interest:
            logger.warning(f"Interest record with ID {interest_id} not found for deletion")
            return False
            
        try:
            db.session.delete(interest)
            db.session.commit()
            logger.info(f"Successfully deleted interest record ID: {interest_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to drop interest record {interest_id}. Error: {str(e)}")
            raise e