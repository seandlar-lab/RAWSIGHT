"""Evidence-only comparison of explicitly aligned event-side series.

Caller supplies BEFORE and AFTER observation bins separately. This function
never discovers anchors, reads a database, resamples, or bridges a gap.
"""
from __future__ import annotations

import math
from typing import Any

from rawsight.pattern_similarity import compare_episodes


def compare_event_contexts(
    target: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    selected_columns: list[str],
    minimum_points: int = 3,
    minimum_coverage: float = 1.0,
    minimum_measured_signals: int = 1,
    max_candidates: int = 100,
) -> dict[str, Any]:
    """Compare aligned before/after event contexts independently.

    Schema per event:
      {"id":"event-a", "before":{"series":{"A":[1,2,3]},
      "alignment":{"method":"observation_index", "bin_count":3}},
      "after":{"series":{"A":[3,2,1]},
      "alignment":{"method":"observation_index", "bin_count":3}}}

    For each side all events must have equal count of explicitly aligned bins,
    and exactly the same alignment method. No automatic time alignment is done.
    Missing or constant signals are excluded and reported, never imputed.
    Full context score is available ONLY if both sides individually qualify.
    """
    if not isinstance(target, dict) or not isinstance(target.get('id'), str) or not target['id']:
        raise ValueError('target.id must be nonempty')
    if not isinstance(candidates, list) or len(candidates) > max_candidates:
        raise ValueError('candidates must be a list within max_candidates')
    if type(max_candidates) is not int or max_candidates < 1:
        raise ValueError('max_candidates must be a positive integer')
    if not isinstance(selected_columns, list) or not selected_columns or not all(isinstance(c,str) and c for c in selected_columns) or len(set(selected_columns)) != len(selected_columns):
        raise ValueError('selected_columns must be unique nonempty names')
    if type(minimum_measured_signals) is not int or not (1 <= minimum_measured_signals <= len(selected_columns)):
        raise ValueError('minimum_measured_signals must be between 1 and the selected signal count')
    if type(minimum_points) is not int or minimum_points < 3:
        raise ValueError('minimum_points must be >= 3')
    if isinstance(minimum_coverage, bool) or not isinstance(minimum_coverage,(int,float)) or not math.isfinite(minimum_coverage) or not (0 < minimum_coverage <= 1):
        raise ValueError('minimum_coverage must be in (0,1]')
    ids = [x.get('id') for x in candidates if isinstance(x,dict)]
    if len(ids) != len(candidates) or any(not isinstance(x,str) or not x or x == target['id'] for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('candidate IDs must be unique nonempty strings distinct from target')

    def validate_side(event: dict[str,Any], side: str) -> tuple[dict[str,Any],dict[str,Any]]:
        obj = event.get(side)
        if not isinstance(obj,dict) or not isinstance(obj.get('series'),dict):
            raise ValueError(f'{event["id"]}.{side}.series must be an object')
        alignment = obj.get('alignment')
        if not isinstance(alignment,dict) or alignment.get('method') not in ('observation_index','elapsed_time_bins'):
            raise ValueError(f'{event["id"]}.{side} requires explicit alignment.method')
        n=alignment.get('bin_count')
        if type(n) is not int or n < minimum_points:
            raise ValueError(f'{event["id"]}.{side} invalid alignment.bin_count')
        if alignment['method'] == 'elapsed_time_bins':
            width=alignment.get('bin_width_seconds')
            if isinstance(width,bool) or not isinstance(width,(int,float)) or not math.isfinite(width) or width <= 0:
                raise ValueError('elapsed_time_bins requires positive bin_width_seconds')
        for col in selected_columns:
            seq=obj['series'].get(col)
            if seq is not None and (not isinstance(seq,list) or len(seq) != n):
                raise ValueError(f'{event["id"]}.{side}.{col} must contain exactly {n} bins')
        return obj,alignment

    scored = {id_: {'candidate_id':id_, 'sides':{}} for id_ in ids}
    for side in ('before','after'):
        target_obj,target_alignment=validate_side(target,side)
        side_candidates=[]
        mismatches={}
        for candidate in candidates:
            obj,alignment=validate_side(candidate,side)
            equal=(target_alignment['method'] == alignment['method'] and target_alignment['bin_count'] == alignment['bin_count'])
            if equal and alignment['method'] == 'elapsed_time_bins':
                equal=(target_alignment['bin_width_seconds'] == alignment['bin_width_seconds'])
            if not equal:
                mismatches[candidate['id']]='incompatible_alignment'
            else:
                side_candidates.append({'id':candidate['id'],'series':obj['series']})
        pattern = compare_episodes(
            {'id':target['id'],'series':target_obj['series']},side_candidates,
            selected_columns=selected_columns, minimum_points=minimum_points,
            minimum_coverage=minimum_coverage,
        )
        by_id={entry['candidate_id']:entry for entry in pattern['candidates']}
        for candidate in candidates:
            id_=candidate['id']
            if id_ in mismatches:
                result={'status':'insufficient_data','shape_similarity':None,'measured_signal_count':0,
                        'requested_signal_count':len(selected_columns),'signals':[],
                        'excluded_signals':[{'column':col,'reason':'incompatible_alignment'} for col in selected_columns]}
            else:
                result=by_id[id_]
                if result['measured_signal_count'] < minimum_measured_signals:
                    result={**result,'status':'insufficient_data','shape_similarity':None,
                            'qualification':'too_few_measured_signals'}
            scored[id_]['sides'][side]=result
    results=[]
    for candidate in candidates:
        item=scored[candidate['id']]
        before=item['sides']['before'];after=item['sides']['after']
        full=(before['status']=='measured' and after['status']=='measured')
        item.update({'status':'measured' if full else 'partial_evidence',
                     'full_context_similarity':(before['shape_similarity']+after['shape_similarity'])/2 if full else None,
                     'scoring':'equal_weight_before_after' if full else None})
        results.append(item)
    results.sort(key=lambda x: (x['full_context_similarity'] is None,
                                -(x['full_context_similarity'] if x['full_context_similarity'] is not None else 0),x['candidate_id']))
    return {'analysis_kind':'event_context_similarity','method':'paired_side_shape_similarity_v0_1',
            'status':'measured' if any(x['status']=='measured' for x in results) else 'insufficient_data',
            'target_id':target['id'],'selected_columns':list(selected_columns),'candidates':results,
            'settings':{'minimum_points':minimum_points,'minimum_coverage':minimum_coverage,
                        'minimum_measured_signals':minimum_measured_signals,'max_candidates':max_candidates},
            'limitations':[
                'The caller supplies verified event anchors and explicitly aligned, equal-bin sequences.',
                'Observation-index alignment is not equivalence of elapsed time or sampling cadence.',
                'No resampling, gap interpolation, imputation, or automatic event discovery is performed.',
                'Before and after are scored independently; a full score requires qualified evidence on BOTH sides.',
                'Mean shape similarity does not establish equal levels, same rates, normality, significance or causality.',
                'No cross-dataset key or temporal alignment is inferred.',
            ]}
