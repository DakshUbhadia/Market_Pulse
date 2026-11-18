import pandas as pd

from quant.pipeline.review_factor_v1 import ranking_review_sample


def test_review_sample_is_distinct_reproducible_and_not_manually_approved():
    scores = pd.DataFrame(dict(instrument_id=[f'id-{i:03}' for i in range(120)],rank=range(1,121)))
    review = ranking_review_sample(scores)
    assert len(review) == 90 and review.instrument_id.is_unique
    assert review.groupby('review_group').size().to_dict() == dict(TOP=30,BOTTOM=30,MIDDLE_RANDOM=30)
    assert review[review.review_group.eq('MIDDLE_RANDOM')]['rank'].between(31,90).all()
    assert review.review_status.eq('NEEDS_MANUAL_REVIEW').all()
    pd.testing.assert_frame_equal(review,ranking_review_sample(scores.sample(frac=1,random_state=15)))
