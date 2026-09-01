# STAGING DEPLOYMENT & VALIDATION PLAN
## Phase 3B Production Rollout

**Status:** ✅ Phase 3B merged to main  
**Date:** September 1, 2026  
**Owner:** Eco Consultor  
**Repository:** https://github.com/Sogo2012/ECO-Wind  

---

## 📋 CHECKLIST PRE-DEPLOYMENT

### Infrastructure Setup
- [ ] Staging environment provisioned (Heroku/Railway/similar)
- [ ] Database backup taken
- [ ] Staging URL configured
- [ ] Environment variables set (usar_gower default = False)
- [ ] SSL/HTTPS verified

### Application Deployment
- [ ] Pull latest main (commit d4885f7)
- [ ] Install production dependencies
- [ ] Run full test suite: `pytest test_phase_b.py -v`
- [ ] Validate syntax: `python -m py_compile app/app.py`
- [ ] Start Streamlit app: `streamlit run app/app.py --server.port 8501`

### Feature Flags & Monitoring
- [ ] Feature flag `usar_gower` = False (default, safe)
- [ ] Logging enabled for method selection
- [ ] Error tracking configured (Sentry/similar)
- [ ] Performance monitoring enabled

### User Communication
- [ ] Release notes prepared
- [ ] In-app notification about new feature
- [ ] Documentation updated
- [ ] Support team briefed

---

## 🧪 VALIDATION PHASE (1-2 weeks)

### Part 1: A/B Testing Setup
```
Cohort A (70%): usar_gower = False (classic Haversine)
Cohort B (30%): usar_gower = True (Gower distance - opt-in)
```

Track metrics:
- User adoption rate of Gower toggle
- Error rates between methods
- User feedback/satisfaction

### Part 2: Real Turbine Validation (Target: 3-5 installations)

#### Required Data Per Turbine
```
1. Site coordinates (lat, lon, elevation)
2. Real wind speed measurements (min 1 month historical)
3. Measured AEP (actual power output)
4. Terrain classification (urban/rural/forest/etc)
5. Historical weather data (if available)
```

#### Validation Metrics
```
For each turbine, compare:

V1 (Old method - Haversine + z0=0.3m):
  - Predicted wind speed
  - Predicted AEP
  - Error vs measured

V1.1 (Phase 3B - Haversine + dynamic z0):
  - Predicted wind speed
  - Predicted AEP
  - Error vs measured

V1.1-Advanced (Phase 3B - Gower + dynamic z0):
  - Predicted wind speed
  - Predicted AEP
  - Error vs measured
```

#### Success Criteria
| Metric | Target | Current | After 3B |
|--------|--------|---------|----------|
| Mean error | ±15% | ±50% | ? |
| Max error | ±30% | ±80% | ? |
| RMSE | Minimal | High | ? |
| Consistency | High | Variable | ? |

### Part 3: Accuracy Analysis

**Sample calculation:**
```
Dodge City (KS):
  Measured AEP (real): 2500 kWh/year
  
  V1 (Haversine + 0.3m):
    Predicted: 1750 kWh/year (error: -30%)
  
  V1.1 (Haversine + dynamic):
    Predicted: 2100 kWh/year (error: -16%) ← Improved
  
  V1.1-Gower (Gower + dynamic):
    Predicted: 2350 kWh/year (error: -6%) ← Better if Gower worked
    (Currently: 2100 because z0/Köppen hardcoded)
```

---

## 📊 REPORTING & DECISION GATES

### Week 1: Setup & Initial Testing
- [ ] Staging environment live
- [ ] App accessible at staging URL
- [ ] Test suite passing
- [ ] Users can toggle Gower method

**Decision Gate:** Can proceed to validation?

### Week 2: A/B Testing & Data Collection
- [ ] 70/30 cohort split active
- [ ] Gower adoption rate tracking
- [ ] Real turbine data collection started

**Decision Gate:** Is data quality sufficient for analysis?

### Week 3-4: Analysis & Rollout Decision

**Three possible outcomes:**

#### Option 1: Haversine Works Well
```
If error reduction is minimal with dynamic z0,
keep default = Haversine
Gower remains as optional advanced feature
No immediate Phase 3C action needed
```

#### Option 2: Gower Shows Clear Improvement
```
If Gower reduces error by >10%:
Change default to usar_gower = True
Maintain Haversine option for compatibility
Prioritize Phase 3C real raster implementation
```

#### Option 3: Results Inconclusive
```
If data is unclear or results mixed:
Keep both methods in A/B testing longer
Collect more turbine data points
Investigate edge cases in complex terrain
Defer default change until Phase 3C
```

---

## 🔧 TECHNICAL CONFIGURATION

### Environment Variables (Staging)
```bash
# .streamlit/config.toml
[theme]
primaryColor = "#0066cc"

[logger]
level = "debug"

# app/config.py
USAR_GOWER_DEFAULT = False  # Safe default
ENABLE_LOGGING = True
LOG_LEVEL = "INFO"
SENTRY_DSN = "https://your-sentry-key@sentry.io/..."
```

### Monitoring Setup
```python
# Log every method selection
if resultado["metodo_seleccion"] == "gower_distance":
    logger.info(f"Gower selected: {lat},{lon} - distance: {resultado['distancia']}")
else:
    logger.info(f"Haversine selected: {lat},{lon} - distance: {resultado['distancia_km']}")

# Track accuracy
logger.info(f"Predicted AEP: {resultado['aep_kwh']} kWh/year")
```

---

## 📝 PHASE 3C TRIGGERS

Implement real raster reading (Phase 3C) **IF**:

1. **Decision Gate 1:** Gower method shows >15% improvement
   - Triggers: Implement real Köppen raster reading
   - Timeline: 2-3 weeks

2. **Decision Gate 2:** Complex terrain sites show high error
   - Triggers: Implement real ESA WorldCover COG reading
   - Timeline: 2-3 weeks

3. **Decision Gate 3:** TPI variance significant for predictions
   - Triggers: Implement DEM-based TPI calculation
   - Timeline: 3-4 weeks

**No Phase 3C action needed if** Haversine + dynamic z0 achieves ±15% error with current hardcoded data.

---

## 🎯 SUCCESS METRICS

### Deployment Success
- ✅ Zero downtime during rollout
- ✅ All tests passing in staging
- ✅ Users can access app without errors
- ✅ Logging working correctly

### Validation Success
- ✅ Data collected from 3+ turbine sites
- ✅ Error analysis complete
- ✅ Method comparison statistically significant
- ✅ Clear recommendation for default method

### Business Success
- ✅ Accuracy improved from ±50% to ±15-20%
- ✅ User adoption of Gower method >20%
- ✅ Positive feedback from real turbine data
- ✅ Confidence in production rollout

---

## 📅 TIMELINE

```
Week 1:  Staging setup + deployment
Week 2:  A/B testing begins + data collection
Week 3:  Analysis phase
Week 4:  Decision & rollout to production
Week 5+: Phase 3C (if triggered) or maintenance mode
```

**Total Duration:** 4-6 weeks  
**Resources Needed:** 1 dev (part-time) + domain expert for turbine data

---

## ⚠️ RISK MITIGATION

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Gower method causes crashes | Low | Already tested, backward compat verified |
| Data collection delays | Medium | Start outreach to turbine owners NOW |
| Haversine remains best method | Medium | Keep Gower as opt-in feature |
| Real raster reading complex | Medium | Phase 3C requires spike/research |
| Users resist method change | Low | A/B testing + optional toggle reduces risk |

---

## 📞 CONTACTS & ESCALATION

**Deployment Authority:** Eco Consultor Team  
**Technical Lead:** Claude Code (ECO-Wind)  
**Data Validation:** Real turbine site owners  
**Decision Maker:** Eco Consultor Director  

---

## APPENDIX: Phase 3C Real Raster Implementation

**When triggered, implement:**

### ESA WorldCover COG Reading (2-3 hours)
```python
# engine/terrain_classification.py - Real implementation
def query_worldcover_z0_real(lat, lon):
    """Query live ESA WorldCover raster via HTTP Range Request"""
    url = "https://storage.googleapis.com/esa_worldcover/2021/esa_worldcover_2021_v200.tif"
    # Use rasterio + COG to fetch single pixel
    with rasterio.open(f"vsis3://{url}") as src:
        pixel = src.read(1, window=((row, row+1), (col, col+1)))
    # Map to Davenport-Wieringa z0
    return WORLDCOVER_Z0_MAP[pixel[0,0]]
```

### Köppen Raster Reading (2-3 hours)
```python
# engine/terrain_classification.py - Real implementation  
def query_koppen_real(lat, lon):
    """Query live Beck et al. 2023 Köppen raster"""
    url = "https://download.worldclim.org/version2_1/wc2.1_30s_bio/..."
    # Similar COG reading approach
```

### DEM-based TPI (3-4 hours)
```python
# engine/terrain_classification.py - Real implementation
def calculate_tpi_real(lat, lon, dem_radius_m=300):
    """Calculate Topographic Position Index from SRTM DEM"""
    # Use elevation APIs to get local DEM
    # Calculate terrain position index
```

---

## CONCLUSION

Phase 3B is **staging-ready**. Execute deployment checklist, validate with real turbine data, then make data-driven decision on default method and Phase 3C implementation timeline.

**Status:** ✅ READY FOR STAGING DEPLOYMENT
