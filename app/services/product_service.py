# app/services.py
import logging
import uuid
from typing import Union, List, Optional
from datetime import datetime
from app.extensions import db
from app.models import Product, Listing, ListingInterest, User, ListingStatus, InterestStatus 

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
        return db.session.get(Product, str(product_id))

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
        return db.session.get(Listing, str(listing_id))

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
                if key == "status" and isinstance(value, str):
                    setattr(listing, key, ListingStatus[value.upper()])
                else:
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

    @staticmethod
    def get_listings_by_seller(seller_id: IdType, status: Optional[str] = None) -> List[Listing]:
        logger.info(f"Fetching listings for seller {seller_id} with status filter: {status}")
        clean_seller_id = str(seller_id).lower()
        query = Listing.query.filter_by(seller_id=clean_seller_id)
        
        if status:
            try:
                status_enum = ListingStatus[status.upper()] if isinstance(status, str) else status
                query = query.filter_by(status=status_enum)
            except KeyError:
                logger.error(f"Invalid listing status filter string provided: {status}")
                return []
                
        return query.order_by(Listing.created_at.desc()).all()
    
    @staticmethod
    def get_by_status(status: Union[ListingStatus, str]) -> List[Listing]:
        """
        Fetches all global listings filtered by a specific marketplace status.
        """
        logger.info(f"Fetching all listings with status: {status}")
        try:
            if isinstance(status, str):
                status_enum = ListingStatus[status.upper()]
            else:
                status_enum = status
                
            return Listing.query.filter_by(status=status_enum)\
                                .order_by(Listing.created_at.desc()).all()
        except KeyError:
            logger.error(f"Invalid listing status string provided: {status}")
            return []


class ListingInterestService:
    @staticmethod
    def create(data: dict) -> ListingInterest:
        logger.info(f"Buyer ID {data.get('buyer_id')} expressing interest in listing ID {data.get('listing_id')}")
        try:
            interest = ListingInterest(**data)
            
            # 1. Hydrate contextual data FIRST while the object is in-memory
            listing = db.session.get(Listing, str(interest.listing_id))
            seller = db.session.get(User, str(listing.seller_id)) if listing else None
            
            if listing and listing.product:
                interest.listing_title = f"{listing.product.brand} {listing.product.model_name}"
            else:
                interest.listing_title = "Unknown Item"
                
            interest.seller_phone = seller.phone if seller else ""
            interest.seller_name = seller.name if seller else "Seller"
            
            # 2. Add and commit everything together cleanly
            db.session.add(interest)
            db.session.commit()
        
            logger.info(f"Successfully created interest tracking entry ID: {interest.id}")
            return interest
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record interest entry. Error: {str(e)}")
            raise e

    @staticmethod
    def get_by_id(interest_id: IdType) -> Optional[ListingInterest]:
        logger.info(f"Fetching interest entry with ID: {interest_id}")
        return db.session.get(ListingInterest, str(interest_id).lower())

    @staticmethod
    def get_all_for_listing(listing_id: IdType) -> List[ListingInterest]:
        logger.info(f"Fetching all active interest expressions/waitlist for listing ID: {listing_id}")
        clean_string_id = str(listing_id).lower()
        return ListingInterest.query.filter_by(listing_id=clean_string_id)\
                                    .order_by(ListingInterest.created_at.asc()).all()

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
        
    @staticmethod
    def get_interests_by_seller_listings(seller_id: IdType) -> List[ListingInterest]:
        logger.info(f"Fetching all received interests for listings owned by seller {seller_id}")
        clean_seller_id = str(seller_id).lower()
        return ListingInterest.query.join(Listing)\
            .filter(Listing.seller_id == clean_seller_id)\
            .order_by(ListingInterest.created_at.desc()).all()

    @staticmethod
    def get_interests_by_buyer(buyer_id: IdType) -> List[ListingInterest]:
        logger.info(f"Fetching all interest expressions sent by buyer {buyer_id}")
        clean_buyer_id = str(buyer_id).lower()
        return ListingInterest.query.filter_by(buyer_id=clean_buyer_id)\
            .order_by(ListingInterest.created_at.desc()).all()   

    @staticmethod
    def get_by_status(status: Union[InterestStatus, str]) -> List[ListingInterest]:
        """
        Fetches all global user interest inquiries filtered by status.
        """
        logger.info(f"Fetching all interest entries with status: {status}")
        try:
            if isinstance(status, str):
                status_enum = InterestStatus[status.upper()]
            else:
                status_enum = status
                
            return ListingInterest.query.filter_by(status=status_enum)\
                                        .order_by(ListingInterest.created_at.desc()).all()
        except KeyError:
            logger.error(f"Invalid interest status string provided: {status}")
            return []

    @staticmethod
    def update_specific_interest(interest_id: IdType, data: dict) -> Optional[ListingInterest]:
        """
        Safely validates and updates fields on a single, specific interest record.
        """
        clean_interest_id = str(interest_id).lower()
        logger.info(f"Attempting to update specific interest record ID: {clean_interest_id}")
        
        interest = ListingInterestService.get_by_id(clean_interest_id)
        if not interest:
            logger.warning(f"Interest record {clean_interest_id} not found for update")
            return None
            
        try:
            for key, value in data.items():
                if key == "status":
                    if isinstance(value, str):
                        setattr(interest, key, InterestStatus[value.upper()])
                    elif isinstance(value, InterestStatus):
                        setattr(interest, key, value)
                else:
                    setattr(interest, key, value)
                    
            db.session.commit()
            logger.info(f"Successfully updated interest record ID: {clean_interest_id}")
            return interest
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update interest record {clean_interest_id}. Error: {str(e)}")
            raise e