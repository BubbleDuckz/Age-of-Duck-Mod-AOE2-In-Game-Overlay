"""Battlefield constraints for description-derived counter suggestions."""
def compatible_target(target, candidate):
    # Melee unique-unit bonuses do not let land units attack ships.
    return ('Warships' not in target.get('member_of', [])
            or 'Warships' in candidate.get('member_of', [])
            or candidate.get('attack_range')!=0)
