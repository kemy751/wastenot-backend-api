# app/services/product_service.py
import logging
import uuid
from sqlalchemy.orm import joinedload
from typing import Union, List, Optional
from datetime import datetime
from app.extensions import db
from app.models.product import Product, Listing, ListingInterest, ListingStatus, InterestStatus
from app.models.user import User
from .green_sustainability import AdvancedGreenEngine

logger = logging.getLogger(__name__)
IdType = Union[uuid.UUID, str]


class ProductService:
    @staticmethod
    def create(data: dict) -> Product:
        try:
            product = Product(**data)
            product.estimated_carbon_saved_kg = AdvancedGreenEngine.calculate_product_impact(product)
            db.session.add(product)
            db.session.commit()
            return product
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_by_id(product_id: IdType) -> Optional[Product]:
        return db.session.get(Product, str(product_id))

    @staticmethod
    def get_all() -> List[Product]:
        return Product.query.all()

    @staticmethod
    def update(product_id: IdType, data: dict) -> Optional[Product]:
        product = ProductService.get_by_id(product_id)
        if not product:
            return None
        try:
            for key, value in data.items():
                setattr(product, key, value)
            db.session.commit()
            return product
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete(product_id: IdType) -> bool:
        product = ProductService.get_by_id(product_id)
        if not product:
            return False
        try:
            db.session.delete(product)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e


class ListingService:
    @staticmethod
    def create(data: dict) -> Listing:
        try:
            listing = Listing(**data)
            db.session.add(listing)
            db.session.commit()
            return listing
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_by_id(listing_id: IdType) -> Optional[Listing]:
        return Listing.query.options(
            joinedload(Listing.images),
            joinedload(Listing.product)
        ).filter_by(id=str(listing_id)).first()

    @staticmethod
    def get_all() -> List[Listing]:
        return Listing.query.options(
            joinedload(Listing.images),
            joinedload(Listing.product)
        ).order_by(Listing.created_at.desc()).all()

    @staticmethod
    def update(listing_id: IdType, data: dict) -> Optional[Listing]:
        listing = ListingService.get_by_id(listing_id)
        if not listing:
            return None
        try:
            for key, value in data.items():
                if key == "status" and isinstance(value, str):
                    setattr(listing, key, ListingStatus[value.upper()])
                else:
                    setattr(listing, key, value)
            db.session.commit()
            return listing
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete(listing_id: IdType) -> bool:
        listing = ListingService.get_by_id(listing_id)
        if not listing:
            return False
        try:
            db.session.delete(listing)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_listings_by_seller(seller_id: IdType, status: Optional[str] = None) -> List[Listing]:
        clean_seller_id = str(seller_id).lower()
        query = Listing.query.filter_by(seller_id=clean_seller_id)
        if status:
            try:
                status_enum = ListingStatus[status.upper()] if isinstance(status, str) else status
                query = query.filter_by(status=status_enum)
            except KeyError:
                return []
        query = query.options(
            joinedload(Listing.images),
            joinedload(Listing.product)
        )
        return query.order_by(Listing.created_at.desc()).all()

    @staticmethod
    def get_by_status(status: Union[ListingStatus, str]) -> List[Listing]:
        try:
            status_enum = ListingStatus[status.upper()] if isinstance(status, str) else status
            return Listing.query.options(
                joinedload(Listing.images),
                joinedload(Listing.product)
            ).filter_by(status=status_enum).order_by(Listing.created_at.desc()).all()
        except KeyError:
            return []


class ListingInterestService:
    @staticmethod
    def create(data: dict) -> ListingInterest:
        try:
            interest = ListingInterest(**data)
            listing = db.session.get(Listing, str(interest.listing_id))
            seller = db.session.get(User, str(listing.seller_id)) if listing else None
            if listing and listing.product:
                interest.listing_title = f"{listing.product.brand} {listing.product.model_name}"
            else:
                interest.listing_title = "Unknown Item"
            interest.seller_phone = seller.phone if seller else ""
            interest.seller_name = seller.name if seller else "Seller"
            db.session.add(interest)
            db.session.commit()
            return interest
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_by_id(interest_id: IdType) -> Optional[ListingInterest]:
        return db.session.get(ListingInterest, str(interest_id).lower())

    @staticmethod
    def get_all_for_listing(listing_id: IdType) -> List[ListingInterest]:
        return ListingInterest.query.filter_by(
            listing_id=str(listing_id).lower()
        ).order_by(ListingInterest.created_at.asc()).all()

    @staticmethod
    def delete(interest_id: IdType) -> bool:
        interest = ListingInterestService.get_by_id(interest_id)
        if not interest:
            return False
        try:
            db.session.delete(interest)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_interests_by_seller_listings(seller_id: IdType) -> List[ListingInterest]:
        clean_seller_id = str(seller_id).lower()
        return ListingInterest.query.options(
            joinedload(ListingInterest.listing).joinedload(Listing.product),
            joinedload(ListingInterest.listing).joinedload(Listing.images),
        ).join(Listing).filter(
            Listing.seller_id == clean_seller_id
        ).order_by(ListingInterest.created_at.desc()).all()

    @staticmethod
    def get_interests_by_buyer(buyer_id: IdType) -> List[ListingInterest]:
        clean_buyer_id = str(buyer_id).lower()
        return ListingInterest.query.options(
            joinedload(ListingInterest.listing).joinedload(Listing.product),
            joinedload(ListingInterest.listing).joinedload(Listing.images),
        ).filter_by(buyer_id=clean_buyer_id).order_by(
            ListingInterest.created_at.desc()
        ).all()

    @staticmethod
    def get_by_status(status: Union[InterestStatus, str]) -> List[ListingInterest]:
        try:
            status_enum = InterestStatus[status.upper()] if isinstance(status, str) else status
            return ListingInterest.query.filter_by(
                status=status_enum
            ).order_by(ListingInterest.created_at.desc()).all()
        except KeyError:
            return []

    @staticmethod
    def update_specific_interest(interest_id: IdType, data: dict) -> Optional[ListingInterest]:
        interest = ListingInterestService.get_by_id(str(interest_id).lower())
        if not interest:
            return None
        try:
            new_status = None
            for key, value in data.items():
                if key == "status":
                    if isinstance(value, str):
                        new_status = InterestStatus[value.upper()]
                        setattr(interest, key, new_status)
                    elif isinstance(value, InterestStatus):
                        new_status = value
                        setattr(interest, key, value)
                else:
                    setattr(interest, key, value)

            # Sync listing status when interest status changes
            if new_status is not None:
                listing = db.session.get(Listing, str(interest.listing_id))
                if listing:
                    if new_status == InterestStatus.APPROVED:
                        # Lock the listing — no more claims accepted
                        listing.status = ListingStatus.PENDING_SALE
                        # Cancel all other EXPRESSED interests for this listing
                        other_interests = ListingInterest.query.filter(
                            ListingInterest.listing_id == listing.id,
                            ListingInterest.id != interest.id,
                            ListingInterest.status == InterestStatus.EXPRESSED,
                        ).all()
                        for other in other_interests:
                            other.status = InterestStatus.CANCELLED
                    elif new_status == InterestStatus.CANCELLED:
                        # If the approved interest is cancelled, revert listing to AVAILABLE
                        if interest.status == InterestStatus.APPROVED or interest.status == InterestStatus.EXPRESSED:
                            # Only revert if no other approved interest exists
                            other_approved = ListingInterest.query.filter(
                                ListingInterest.listing_id == listing.id,
                                ListingInterest.id != interest.id,
                                ListingInterest.status == InterestStatus.APPROVED,
                            ).first()
                            if not other_approved and listing.status == ListingStatus.PENDING_SALE:
                                listing.status = ListingStatus.AVAILABLE

            db.session.commit()
            return interest
        except Exception as e:
            db.session.rollback()
            raise e