from fastapi import APIRouter

from app.api.v1 import favorites, insights, inventory, planning, profile, recommendations, workouts

router = APIRouter(prefix="/api/v1")
router.include_router(profile.router)
router.include_router(inventory.router)
router.include_router(planning.router)
router.include_router(workouts.router)
router.include_router(recommendations.router)
router.include_router(favorites.router)
router.include_router(insights.router)

