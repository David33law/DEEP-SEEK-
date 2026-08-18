"""Apply the owner-signed Observatory workload policy to evaluator overlays."""
from . import observatory_crown_overlay as crown
from . import observatory_distributed_overlay as distributed
from . import observatory_formal_overlay as formal
from . import observatory_interoperability_overlay as interoperability
from . import observatory_protocol as protocol
from . import observatory_scale_overlay as scale


def apply():
    crown.SYSTEMS_QUAL_EVENTS = protocol.workload("systems", "qualification")
    crown.SYSTEMS_REPLICATION_EVENTS = protocol.workload("systems", "replication")
    crown.SYSTEMS_CROWN_EVENTS = protocol.workload("systems", "crown")
    distributed.DISTRIBUTED_QUAL_EVENTS = protocol.workload("distributed", "qualification")
    distributed.DISTRIBUTED_REPLICATION_EVENTS = protocol.workload("distributed", "replication")
    distributed.DISTRIBUTED_CROWN_EVENTS = protocol.workload("distributed", "crown")
    scale.SCALE_QUAL_EVENTS = protocol.workload("scale", "qualification")
    scale.SCALE_REPLICATION_EVENTS = protocol.workload("scale", "replication")
    scale.SCALE_CROWN_EVENTS = protocol.workload("scale", "crown")
    scale.SCALE_PARTITIONS = protocol.workload("scale", "partitions")
    scale.SCALE_BATCH = protocol.workload("scale", "batch")
    formal.FORMAL_QUAL_DEPTH = protocol.workload("formal", "qualification_depth")
    formal.FORMAL_REPLICATION_DEPTH = protocol.workload("formal", "replication_depth")
    formal.FORMAL_CROWN_DEPTH = protocol.workload("formal", "crown_depth")
    interoperability.QUAL_CASES = protocol.workload("interoperability", "qualification_cases")
    interoperability.REPLICATION_CASES = protocol.workload("interoperability", "replication_cases")
    interoperability.CROWN_CASES = protocol.workload("interoperability", "crown_cases")
    return snapshot()


def snapshot():
    return {
        "proof_mode": protocol.proof_mode(),
        "systems": {
            "qualification": crown.SYSTEMS_QUAL_EVENTS,
            "replication": crown.SYSTEMS_REPLICATION_EVENTS,
            "crown": crown.SYSTEMS_CROWN_EVENTS,
            "crash_events": protocol.workload("systems", "crash_events")},
        "distributed": {
            "qualification": distributed.DISTRIBUTED_QUAL_EVENTS,
            "replication": distributed.DISTRIBUTED_REPLICATION_EVENTS,
            "crown": distributed.DISTRIBUTED_CROWN_EVENTS,
            "crash_events": protocol.workload("distributed", "crash_events")},
        "scale": {
            "qualification": scale.SCALE_QUAL_EVENTS,
            "replication": scale.SCALE_REPLICATION_EVENTS,
            "crown": scale.SCALE_CROWN_EVENTS,
            "partitions": scale.SCALE_PARTITIONS,
            "batch": scale.SCALE_BATCH},
        "formal": {
            "qualification_depth": formal.FORMAL_QUAL_DEPTH,
            "replication_depth": formal.FORMAL_REPLICATION_DEPTH,
            "crown_depth": formal.FORMAL_CROWN_DEPTH},
        "interoperability": {
            "qualification_cases": interoperability.QUAL_CASES,
            "replication_cases": interoperability.REPLICATION_CASES,
            "crown_cases": interoperability.CROWN_CASES},
        "cross_model": {
            "qualification_histories": protocol.workload(
                "cross_model", "qualification_histories"),
            "replication_histories": protocol.workload(
                "cross_model", "replication_histories"),
            "crown_histories": protocol.workload(
                "cross_model", "crown_histories")}}
