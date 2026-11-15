# Ford Scorpion

## Buffer

| name | init | capacity |
| --- | --- | --- |
| buffer #1 | 0 | 8 |
| buffer #2 | 0 | 8 |
| buffer #3 | 0 | 8 |
| buffer #4 | 0 | 8 |
| buffer #5 | 0 | 16 |
| buffer #6 | 0 | 6 |

## Machine

### CU-115

#### Connections

| inlet | outlet |
| --- | --- |
| - | buffer #1 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.1616 | 0.5394666666666668 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.6997226796002396 | 0.9058507998163218 | - | hours | - | - |

### CU-075

#### Connections

| inlet | outlet |
| --- | --- |
| - | buffer #1 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.2984 | 0.5572 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 336 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 0.5665742265334132 | 0.30195026660544055 | - | hours | - | - |

### CU-201

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #1 | buffer #2 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 3.9456 | 0.5114666666666667 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.6997226796002396 | 0.9058507998163218 | - | hours | - | - |

### CU-192

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #1 | buffer #2 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 3.7728 | 0.48906666666666676 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.6997226796002396 | 0.9058507998163218 | - | hours | - | - |

### CU-133

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #2 | buffer #3 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.2696 | 0.5534666666666667 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 0.5665742265334132 | 0.30195026660544055 | - | hours | - | - |

### CU-119

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #2 | buffer #3 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.3632 | 0.5656 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 0.5665742265334132 | 0.30195026660544055 | - | hours | - | - |

### FR-160

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #3 | buffer #4 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 1.7999999999999998 | 0.23333333333333336 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 224 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.6997226796002396 | 0.9058507998163218 | - | hours | - | - |

### CU-120

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #4 | buffer #5 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.4712 | 0.5796 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 224 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.4164355663335328 | 0.7548756665136014 | - | hours | - | - |

### CU-121

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #4 | buffer #5 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.3488 | 0.5637333333333334 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.4164355663335328 | 0.7548756665136014 | - | hours | - | - |

### CU-134

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #5 | buffer #6 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.3488 | 0.5637333333333334 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.6997226796002396 | 0.9058507998163218 | - | hours | - | - |

### CU-135

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #5 | buffer #6 |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 4.5216 | 0.5861333333333334 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 1.6997226796002396 | 0.9058507998163218 | - | hours | - | - |

### FR-113

#### Connections

| inlet | outlet |
| --- | --- |
| buffer #6 | - |

#### Parameters

| name | parameter | type | distribution | mean | std | value | unit | probability | every |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | normal | 2.1672 | 0.2809333333333333 | - | minutes | - | - |
| maintenance | trigger | operating_time | exponential | 200 | - | - | hours | - | - |
| maintenance | time_to_repair | - | lognormal | 0.5665742265334132 | 0.30195026660544055 | - | hours | - | - |

## Output

| parameter | value |
| --- | --- |
| output_dir | results |
| csv | true |
| plots | true |
