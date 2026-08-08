# MVP V1 User Stories — Recovery Meal Recommendation

## MVP Goal

Enable a user to upload a GPX workout file and receive practical recovery meal recommendations based on:

* Workout duration and intensity
* Estimated energy expenditure
* Basic physical profile
* Fitness goal
* Dietary restrictions
* Favorite foods
* Food currently available at home
* Maximum preparation time

The MVP should answer one question well:

**“Given the workout I just completed and what I have available, what should I eat now?”**

---

# Epic 1 — User Profile

## US-1.1 Create Physical Profile

**As a user,**
I want to enter my basic physical information
**so that** the application can personalize workout and recovery calculations.

### Acceptance Criteria

* User can enter:

  * Age
  * Sex
  * Height
  * Weight
* Height and weight support commonly used US and metric units.
* Required fields are validated.
* Profile is persisted.
* User can return later and view the saved profile.

### Out of Scope

* HealthKit integration
* Medical history
* Body-fat percentage
* VO2 max
* Wearable-device synchronization

---

## US-1.2 Define Fitness Goal

**As a user,**
I want to specify my primary fitness goal
**so that** meal recommendations reflect what I am trying to accomplish.

### Supported Goals

* Maintain weight
* Lose weight
* Gain muscle
* Improve endurance/performance

### Acceptance Criteria

* User can select one primary goal.
* Selected goal is saved with the profile.
* Goal is included when calculating recovery recommendations.
* User can change the goal later.

---

## US-1.3 Define Dietary Restrictions

**As a user,**
I want to identify foods I cannot or do not want to eat
**so that** the app does not recommend inappropriate meals.

### Supported MVP Restrictions

* Vegetarian
* Vegan
* Dairy-free
* Gluten-free
* No restriction

User may also enter specific foods to avoid.

### Acceptance Criteria

* User can select zero or more dietary restrictions.
* User can enter a simple list of foods to avoid.
* Restricted foods must not appear in recommended meals.
* Restrictions are persisted with the user profile.

---

# Epic 2 — Food Preferences

## US-2.1 Add Favorite Foods

**As a user,**
I want to record foods and meals I enjoy
**so that** recommendations are more likely to match my preferences.

### Acceptance Criteria

* User can enter favorite foods using free text.
* Example entries:

  * Chicken
  * Rice
  * Pasta
  * Eggs
  * Greek yogurt
  * Mexican food
  * Chinese food
* Favorite foods are persisted.
* User can add or remove favorites.
* Meal recommendation logic receives the favorites as preference context.

### MVP Simplification

No sophisticated preference scoring is required.

A food is either:

* Favorite
* Neutral
* Avoid

---

# Epic 3 — Available Food

## US-3.1 Maintain Available Food List

**As a user,**
I want to tell the app what food I currently have available
**so that** it can recommend meals I can actually prepare.

### Acceptance Criteria

* User can manually add food items.

* Each item requires only a name.

* Example:

  * Chicken breast
  * Eggs
  * Rice
  * Banana
  * Milk
  * Greek yogurt
  * Spinach

* User can remove items.

* Food list is persisted.

* Recommendation engine can retrieve the current list.

### MVP Simplification

Do not track:

* Quantity
* Expiration date
* Storage location
* Brand
* Barcode
* Nutrition label
* Purchase history

Presence or absence is sufficient for V1.

---

# Epic 4 — GPX Workout Upload

## US-4.1 Upload GPX File

**As a user,**
I want to upload a GPX file from a completed workout
**so that** the application can analyze my exercise.

### Acceptance Criteria

* User can select a `.gpx` file from their device.
* App validates that the uploaded file is a readable GPX file.
* Invalid files generate a clear error message.
* Successful upload creates a workout record.
* Original GPX file may be retained for troubleshooting but is not required to remain permanently.

---

## US-4.2 Extract Workout Data

**As a user,**
I want the app to extract basic workout information from my GPX file
**so that** I do not have to enter workout details manually.

### Required Extracted Fields

Where available:

* Workout start time
* Duration
* Moving duration
* Distance
* Elevation gain
* Average speed or pace
* Heart-rate data

### Acceptance Criteria

* Distance is calculated from GPX track points.
* Duration is determined from GPX timestamps.
* Elevation gain is calculated when elevation data exists.
* Heart-rate data is optional.
* Missing optional GPX data does not cause the upload to fail.
* Extracted values are stored with the workout.

---

# Epic 5 — Workout Analysis

## US-5.1 Classify Workout Intensity

**As a user,**
I want the app to characterize the intensity of my workout
**so that** recovery requirements reflect how demanding the activity was.

### MVP Output

Workout intensity:

* Low
* Moderate
* High

### Acceptance Criteria

* Intensity is calculated using deterministic application logic.
* Duration and available GPX metrics contribute to the calculation.
* Heart-rate data may improve the result when available.
* The LLM is not responsible for calculating workout intensity.
* Result is stored with the workout.

---

## US-5.2 Estimate Energy Expenditure

**As a user,**
I want an estimate of how much energy I expended during the workout
**so that** the app can estimate my recovery needs.

### Acceptance Criteria

* Estimate considers:

  * User weight
  * Workout duration
  * Activity intensity
* Result is presented as an estimate rather than an exact measurement.
* App may display either:

  * A calorie range, or
  * An approximate calorie value
* The calculation is deterministic.
* LLM is not responsible for estimating calories.

### Example

> Estimated workout expenditure: 900–1,100 kcal

---

## US-5.3 Display Workout Summary

**As a user,**
I want to see what the app understood about my workout
**so that** I can verify the analysis before receiving meal recommendations.

### Acceptance Criteria

App displays:

* Duration
* Distance
* Elevation gain, when available
* Intensity
* Estimated energy expenditure
* Average heart rate, when available

User can continue to meal recommendations from this screen.

---

# Epic 6 — Recovery Target

## US-6.1 Calculate Recovery Needs

**As a user,**
I want the application to estimate my recovery recovery needs
**so that** recommended meals are appropriate for the workout I completed.

### MVP Recovery Targets

The system should determine approximate targets for:

* Calories
* Protein
* Carbohydrates

Optional:

* Fluid recommendation

### Acceptance Criteria

Recovery targets consider:

* Workout duration
* Workout intensity
* Estimated expenditure
* User weight
* User fitness goal

Targets are expressed as ranges where appropriate.

### Example

> Recovery target
> Calories: 600–800 kcal
> Protein: 25–35 g
> Carbohydrates: 80–110 g

### Important Rule

The system must not assume that all workout calories need to be immediately replaced.

---

# Epic 7 — Meal Recommendation

## US-7.1 Specify Available Preparation Time

**As a user,**
I want to tell the app how much time I have to prepare food
**so that** it recommends meals that fit my immediate situation.

### Supported MVP Options

* 5 minutes
* 15 minutes
* 30 minutes
* No preference

### Acceptance Criteria

* User selects one option before requesting recommendations.
* Preparation time becomes a recommendation constraint.
* Meals requiring substantially more time should not be recommended.

---

## US-7.2 Generate Recovery Meal Recommendations

**As a user,**
I want several meal suggestions based on my workout and available food
**so that** I can quickly decide what to eat.

### Acceptance Criteria

The system generates up to three recommendations.

Recommendation context includes:

* Recovery target
* Available food
* Favorite food
* Dietary restrictions
* Foods to avoid
* Preparation-time limit
* Fitness goal

Each recommendation contains:

* Meal name
* Ingredients
* Basic preparation instructions
* Estimated preparation time
* Estimated calories
* Estimated protein
* Estimated carbohydrates
* Short explanation of why it fits the workout

### Example

**Chicken & Rice Recovery Bowl**

18 minutes

Uses:

* Chicken
* Rice
* Spinach
* Egg

Approximate nutrition:

* 720 kcal
* 38 g protein
* 96 g carbohydrates

Why this works:

> Your workout created a relatively high carbohydrate recovery requirement. Rice helps replenish carbohydrates while chicken and egg provide sufficient protein for recovery.

---

## US-7.3 Prioritize Available Ingredients

**As a user,**
I want recommendations to favor food I already have
**so that** I can eat without another shopping trip.

### Acceptance Criteria

* Meals using only available ingredients rank above meals requiring missing ingredients.
* A recommendation may contain one or two missing optional ingredients if the meal still makes sense without them.
* Required missing ingredients must be clearly identified.
* At least one recommended option should use only available food whenever a reasonable meal can be constructed.

---

## US-7.4 Respect Dietary Constraints

**As a user,**
I want all generated meals to comply with my dietary restrictions
**so that** I can safely consider the recommendations.

### Acceptance Criteria

* Recommendation generation receives dietary restrictions as hard constraints.
* Foods explicitly marked “avoid” must not be recommended.
* Recommendations violating dietary restrictions must be rejected before being displayed.

---

# Epic 8 — Recommendation Presentation

## US-8.1 Compare Meal Options

**As a user,**
I want a small number of clearly differentiated choices
**so that** I can make a decision without analyzing many recipes.

### MVP Recommendation Categories

Where possible, present:

**Best Recovery Match**

The meal that best matches the recovery target.

**Fastest**

The acceptable meal requiring the least preparation.

**Best Use of What I Have**

The meal maximizing current ingredient availability.

### Acceptance Criteria

* Maximum of three options are displayed.
* Each option explains why it was selected.
* Categories may point to the same meal if insufficient alternatives exist.
* The UI must not present a long list of recipes.

---

## US-8.2 View Meal Preparation Instructions

**As a user,**
I want simple instructions for the selected meal
**so that** I can start preparing it immediately.

### Acceptance Criteria

* User can open a recommended meal.
* App displays:

  * Ingredients
  * Approximate quantities
  * Simple preparation steps
  * Preparation time
  * Approximate nutrition
* Recipe should favor simple preparation over elaborate cooking techniques.

---

# Epic 9 — Recommendation Feedback

## US-9.1 Select a Recommended Meal

**As a user,**
I want to indicate which recommendation I chose
**so that** the application can retain the outcome.

### Acceptance Criteria

* User can select “I'll make this.”
* Selected recommendation is recorded.
* Selection is associated with the workout.
* Only one selected meal is required for V1.

### Why Include This in V1

The MVP does not need personalization learning yet.

However, collecting this data now creates the foundation for learning later:

```text
Workout → Recommendations → User Selection
```

---

# Epic 10 — Basic System Safety and Transparency

## US-10.1 Clearly Identify Estimates

**As a user,**
I want to understand which values are estimates
**so that** I do not mistake the application for a medical measurement device.

### Acceptance Criteria

The UI clearly identifies estimated values including:

* Energy expenditure
* Macronutrient requirements
* Meal nutrition

The application does not present recommendations as medical advice.

---

## US-10.2 Prevent AI From Inventing User Data

**As a system owner,**
I want the AI to use only supplied application data
**so that** recommendations are based on known user context.

### Acceptance Criteria

* User profile comes from stored application data.
* Workout information comes from the workout analysis service.
* Available ingredients come from stored inventory.
* Recovery targets come from deterministic calculation.
* The LLM may generate and explain meals.
* The LLM must not invent:

  * Workout metrics
  * User physical characteristics
  * Available ingredients
  * Dietary restrictions

---

# MVP End-to-End Story

The primary implementation scenario should be testable as a single workflow:

### Given

A user has:

* Weight: 180 lb
* Goal: maintain weight
* Favorite foods: chicken, rice, eggs, Asian food
* Avoids seafood
* Available food:

  * Chicken breast
  * Rice
  * Eggs
  * Spinach
  * Banana
  * Greek yogurt

### When

The user:

1. Uploads a valid cycling GPX file.
2. The workout is analyzed as:

   * 42 miles
   * 2 hours 30 minutes
   * High intensity
   * Approximately 1,500 kcal expenditure.
3. Selects a maximum preparation time of 20 minutes.
4. Requests meal recommendations.

### Then

The application:

1. Calculates the recovery target.
2. Uses the profile and inventory.
3. Produces no more than three meal recommendations.
4. Prioritizes meals using available ingredients.
5. Does not recommend seafood.
6. Shows estimated calories, protein and carbohydrates.
7. Explains why each meal fits the workout.
8. Allows the user to select one meal.

---

# V1 Explicitly Out of Scope

To prevent MVP scope creep, the following should not be implemented in Version 1:

* Strava integration
* Garmin integration
* Apple Health / HealthKit
* Restaurant search
* DoorDash / Uber Eats
* Pickup-time calculation
* Grocery ordering
* Barcode scanning
* Refrigerator image recognition
* Receipt scanning
* Ingredient quantity tracking
* Expiration-date optimization
* Weather-based hydration
* Weekly training-load analysis
* Meal history analysis
* Automated preference learning
* Vector database
* RAG
* Multiple autonomous agents
* Push notifications
* Social features
* Nutrition-provider integrations

---

# Recommended Implementation Order

### Sprint 1 — Establish the data path

* US-1.1 Physical profile
* US-1.2 Fitness goal
* US-1.3 Dietary restrictions
* US-2.1 Favorite foods
* US-3.1 Available food

**Milestone:** The application knows enough about the user to personalize recommendations.

### Sprint 2 — Understand the workout

* US-4.1 GPX upload
* US-4.2 GPX extraction
* US-5.1 Workout intensity
* US-5.2 Energy expenditure
* US-5.3 Workout summary

**Milestone:** Uploading a GPX file produces a credible workout summary.

### Sprint 3 — Build the recovery engine

* US-6.1 Recovery needs
* US-10.1 Estimate transparency

**Milestone:** A workout produces a structured recovery target without using GenAI.

### Sprint 4 — Add GenAI

* US-7.1 Preparation time
* US-7.2 Meal generation
* US-7.3 Available-ingredient prioritization
* US-7.4 Dietary constraints
* US-10.2 AI grounding

**Milestone:** The application answers, “What should I eat now?”

### Sprint 5 — Make it usable

* US-8.1 Compare recommendations
* US-8.2 Preparation instructions
* US-9.1 Select meal

**Milestone:** Complete MVP workflow from workout upload through meal selection.

---

# MVP Definition of Done

Version 1 is done when a new user can complete this sequence without developer intervention:

**Create profile → Enter available food → Upload GPX → See workout analysis → Request recommendation → Receive three relevant meals → Select one**

The success criterion should not be architectural sophistication.

The success criterion is whether the meal recommendations are sufficiently useful that a real user would act on them after finishing a workout.
