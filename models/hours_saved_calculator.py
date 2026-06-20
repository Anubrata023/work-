"""
M/D/1 Queuing Theory Traffic Flow & Commuter Delay Calculator
Models average vehicle queuing delay and commuter hours saved after enforcement action.
"""
import numpy as np

def calculate_md1_delay(arrival_rate, service_rate, duration_hours=3.0):
    """
    Calculates average delay (in hours) per vehicle using M/D/1 queuing theory.
    W = 1/mu + lambda / (2 * mu * (mu - lambda))
    For oversaturated conditions (arrival_rate >= service_rate), we use a deterministic
    queuing approximation to model the growing queue delay.
    """
    if service_rate <= 0:
        return duration_hours  # Absolute blockage cap

    rho = arrival_rate / service_rate
    
    if rho < 0.95:
        # Standard M/D/1 steady state delay equation
        delay = 1.0 / service_rate + arrival_rate / (2.0 * service_rate * (service_rate - arrival_rate))
    else:
        # Oversaturated queue approximation (time-dependent queue behavior)
        # Average delay includes service time, queuing time near capacity, plus deterministic queue build up
        rho_cap = 0.95
        steady_state_delay = 1.0 / service_rate + (rho_cap * service_rate) / (2.0 * service_rate * (service_rate - rho_cap * service_rate))
        
        # Deterministic queue growth delay component for duration T:
        # Avg queue length growth rate = (lambda - mu)
        # Average queue size = (lambda - mu) * T / 2
        # Average delay = (lambda - mu) * T / (2 * mu)
        deterministic_delay = max(0.0, (arrival_rate - service_rate) * duration_hours / (2.0 * service_rate))
        delay = steady_state_delay + deterministic_delay
        
    return min(delay, duration_hours) # Cap maximum delay at the duration of the analysis window

def calculate_hours_saved(violations_before, violations_after, baseline_count, duration_hours=3.0, hourly_volume=1000.0):
    """
    Calculates total commuter-hours saved by reducing violations.
    - arrival_rate (lambda) is based on hourly traffic volume.
    - service_rate (mu) is reduced by active violations.
    Uses an exponential decay model to simulate capacity degradation:
      mu = mu_nominal * (0.2 + 0.8 * exp(-0.002 * violations))
    """
    arrival_rate = float(hourly_volume)
    
    # Nominal capacity of the road segment (e.g. 1.25 times arrival rate)
    nominal_capacity = max(100.0, arrival_rate * 1.25)
    
    # Exponential decay model for actual capacity (diminishing marginal reduction)
    # The capacity decays from 100% down to a floor of 20% under extreme violation loads.
    service_rate_before = nominal_capacity * (0.2 + 0.8 * np.exp(-0.002 * float(violations_before)))
    service_rate_after = nominal_capacity * (0.2 + 0.8 * np.exp(-0.002 * float(violations_after)))
    
    delay_before_hr = calculate_md1_delay(arrival_rate, service_rate_before, duration_hours)
    delay_after_hr = calculate_md1_delay(arrival_rate, service_rate_after, duration_hours)
    
    # Time saved per vehicle in hours
    time_saved_per_vehicle = max(0.0, delay_before_hr - delay_after_hr)
    
    # Total hours saved = total vehicles * time saved per vehicle
    total_vehicles = arrival_rate * duration_hours
    total_hours_saved = total_vehicles * time_saved_per_vehicle
    
    return round(float(total_hours_saved), 1)

if __name__ == "__main__":
    # Standard validation execution
    print("Testing M/D/1 Queuing Math Calculator...")
    v_before = 8.0
    v_after = 2.0
    saved = calculate_hours_saved(v_before, v_after, baseline_count=3.0, duration_hours=3.0, hourly_volume=1000.0)
    print(f"Violations: {v_before} -> {v_after} | Hours Saved: {saved} hrs")
