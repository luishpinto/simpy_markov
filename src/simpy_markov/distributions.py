"""Campionamento e validazione delle distribuzioni temporali."""
import math

UNITS = {'seconds': 0.0002777777777777778, 'minutes': 0.016666666666666666, 'hours': 1.0}

def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label}: richiesto un numero')
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f'{label}: valore non valido {value}')
    return value


def validate_distribution(spec, positive=False):
    if not isinstance(spec, dict):
        raise ValueError('La distribuzione deve essere un oggetto')
    kind = spec.get('distribution')
    if spec.get('unit') not in UNITS:
        raise ValueError('Unità consentite: seconds, minutes, hours')
    if kind == 'fixed':
        mean = number(spec.get('value'), 'value')
    elif kind in ('normal', 'lognormal', 'exponential'):
        mean = number(spec.get('mean'), 'mean')
        if kind != 'exponential':
            std = number(spec.get('std'), 'std')
            if kind == 'lognormal' and mean == 0 and std != 0:
                raise ValueError('Lognormale: mean deve essere positivo se std > 0')
    else:
        raise ValueError(f'Distribuzione sconosciuta: {kind}')
    if (positive or kind == 'exponential') and mean <= 0:
        raise ValueError('La media deve essere positiva')


def sample(spec, rng, positive=False):
    """Lognormale parametrizzata con media e deviazione fisiche, non logaritmiche."""
    kind = spec['distribution']
    for _ in range(1000):
        if kind == 'fixed':
            value = spec['value']
        elif kind == 'normal':
            value = rng.gauss(spec['mean'], spec['std'])
        elif kind == 'exponential':
            value = rng.expovariate(1 / spec['mean'])
        else:
            mean, std = spec['mean'], spec['std']
            if std == 0:
                value = mean
            else:
                sigma2 = math.log1p((std / mean) ** 2)
                value = rng.lognormvariate(math.log(mean) - sigma2 / 2, math.sqrt(sigma2))
        value *= UNITS[spec['unit']]
        if not math.isfinite(value):
            raise ValueError('Campione non finito: verificare i parametri')
        if not positive:
            return max(0.0, value)
        if value > 0:
            return value
    raise ValueError('Impossibile campionare un tempo strettamente positivo')
