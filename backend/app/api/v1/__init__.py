from fastapi import APIRouter

from app.api.v1 import inventory, profile, recommendations, workouts

router = APIRouter(prefix="/api/v1")
router.include_router(profile.router)
router.include_router(inventory.router)
router.include_router(workouts.router)
router.include_router(recommendations.router)

