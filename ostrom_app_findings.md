# Ostrom app 6.4.0 (com.ostrommobile) - static findings

Source: APKPure xapk, Hermes bytecode v96 bundle (React Native). Strings extracted with tools/hbc_strings.py.
No requests were sent to Ostrom. Everything here is from static analysis; payloads/hosts-per-endpoint are NOT yet verified.

## Base URLs (found in classes7.dex)
- https://api.ostrom.de/v1   (main app backend, presumably)
- https://vpp.ostrom.de/v1   (virtual power plant / NeoGrid, presumably)
- https://vpp-beta.ostrom.de/v1
- (Voltik legacy: api.voltik.de / vpp.voltik.de)

## Path strings in the JS bundle (REST, not GraphQL)
```
/active-contract
/auth/check-face-id-public-key
/auth/check-user-code
/auth/delete-face-id-public-key
/auth/face-id-public-key
/auth/login
/auth/login-email
/auth/login-reset-password
/auth/login-sms
/auth/password
/auth/refresh
/batteries
/batteries/
/chargers
/chargers/
/charging-pair
/configurations/version-support
/contracts
/contracts/
/hems
/hems/
/hvacs
/hvacs/
/meters
/meters/
/perks
/perks/
/power-cloud-action/
/production-statistics/
/schedules
/smart-devices/authorization
/smart-devices/authorization?gateway=
/smart-devices/batteries
/smart-devices/batteries/
/smart-devices/contract-locations
/smart-devices/contract-locations/
/smart-devices/energy-flow
/smart-devices/energy-flow/graph
/smart-devices/energy-flow/refresh
/smart-devices/link
/smart-devices/link?gateway=vaillant
/smart-devices/link?gateway=viessmann
/smart-devices/schedules
/smart-devices/schedules/
/smart-devices/schedules?gateway=
/smart-devices/smart-charging-override
/smart-devices/validate-login-code?gateway=viessmann
/smart-devices/validate-login-code?gateway=viessmann&code=
/smart-devices/vehicles/
/smart-meters/
/vehicles
/vehicles/
```

## Decompiled (hbc-decompiler, bundle v96) - verified from code, not yet against the live API

### Auth
- `POST /auth/login` body `{email, password, application}`, `credentials: include` (session cookies are stored by the app: `storeAuthenticationCookies`)
- `POST /auth/login-email` `{email, language}` (passwordless/code), `POST /auth/password` `{email, password, code}`, `POST /auth/check-user-code` `{email, code, language}`
- `POST /auth/refresh` with header `X-SESSION-TOKEN: <refresh_token>`
- Unknown yet: value of `application`, exact response/cookie names, which base URL (api vs vpp) each path uses.

### Device control (axios, base URL = getApiUrl())
```
completeViessmannHvacLogin             post   /smart-devices/validate-login-code?gateway=viessmann&code=
connectViessmannHvac                   post   /smart-devices/link?gateway=viessmann
controlCharging                        put    /vehicles/ + /control-charging
createSmartDeviceSchedules             post   /smart-devices/schedules?gateway=
createVaillantHvac                     post   /smart-devices/link?gateway=vaillant
deleteSmartChargingOverride            delete /smart-devices/smart-charging-override
deleteSmartDeviceSchedule              delete /smart-devices/schedules/ + ?gateway=
disconnectSmartDevices                 delete /smart-devices/authorization?gateway=
getBatteries                           get    /batteries
getBatteryById                         get    /batteries/
getChargerById                         get    /chargers/
getDeviceFlowGraphData                 get    /smart-devices/energy-flow/graph
getEnergyFlow                          get    /smart-devices/energy-flow
getHVACById                            get    /hvacs/ + ?gateway=
getHVACs                               get    /hvacs
getMeterById                           get    /meters/
getMeters                              get    /meters
getSmartDeviceSchedules                get    /smart-devices/schedules
getSolarProductionData                 get    /production-statistics/ + ?day= + &month= + &year=
refreshDeviceFlowGraphData             put    /smart-devices/energy-flow/refresh
refreshEnergyFlow                      put    /smart-devices/energy-flow/refresh
startSmartChargingOverride             post   /smart-devices/smart-charging-override
submitNote                             put    /power-cloud-action/ + /notes
updateCharger                          put    /chargers/
updateHVACMode                         post   /hvacs/ + /permanent-hold?gateway=
updateSmartDeviceSchedule              put    /smart-devices/schedules/ + ?gateway=
updateVehicle                          put    /vehicles/
updateVehicleLocation                  put    /smart-devices/contract-locations/
updateVehicleNeoGridState              put    /vehicles/
verifyPowerCloudAction                 put    /power-cloud-action/
```
- Vehicle/charger settings body: `{optimizedCharging, requiredForUseAt, batteryLevelNeeded, zip, street, houseNumber, city}` (PUT /vehicles/{id}); chargers only `{optimizedCharging, requiredForUseAt}`
- `PUT /vehicles/{id}/control-charging` body `{action: EVChargingStatus.START|STOP}` (enum string values not yet confirmed)
- `POST|DELETE /smart-devices/smart-charging-override` (payload not yet found; UI caller in query key `smart-charging-override`)
