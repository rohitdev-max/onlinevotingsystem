from datetime import timedelta, timezone

from sqlalchemy import and_, case, func

from app import db
from app.models import AuditLog, User, Vote, VoterEligibility
from app.services.time import INDIA_TIMEZONE, india_now_naive


def get_live_election_stats(election):
    """Return aggregate election participation without voter or candidate details."""
    now = india_now_naive()
    total_verified_voters = (
        VoterEligibility.query
        .join(User, User.id == VoterEligibility.voter_id)
        .filter(
            VoterEligibility.election_id == election.id,
            VoterEligibility.verified.is_(True),
            User.kyc_status == 'VERIFIED',
            User.face_auth_status == 'VERIFIED',
        )
        .count()
    )
    votes_query = Vote.query.filter_by(election_id=election.id)
    votes_cast = votes_query.count()

    if election.status in {'CLOSED', 'RESULTS_PUBLISHED'} or now > election.end_time:
        status = 'ENDED'
    elif election.status == 'OPEN' and election.start_time <= now <= election.end_time:
        status = 'LIVE'
    else:
        status = 'UPCOMING'

    participation = []
    duration = (election.end_time - election.start_time).total_seconds()
    if duration > 0:
        utc_start = election.start_time.replace(tzinfo=INDIA_TIMEZONE).astimezone(timezone.utc).replace(tzinfo=None)
        bucket_expressions = []
        for index in range(12):
            bucket_start = utc_start + timedelta(seconds=duration * index / 12)
            bucket_end = utc_start + timedelta(seconds=duration * (index + 1) / 12)
            if index == 11:
                bucket_end += timedelta(microseconds=1)
            bucket_expressions.append(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Vote.election_id == election.id,
                                    Vote.created_at >= bucket_start,
                                    Vote.created_at < bucket_end,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                )
            )
        bucket_counts = db.session.query(*bucket_expressions).select_from(Vote).one()
        participation = [
            {
                'label': (
                    election.start_time
                    + timedelta(seconds=duration * index / 12)
                ).strftime('%d %b %H:%M'),
                'votes': int(count),
            }
            for index, count in enumerate(bucket_counts)
        ]

    audited_votes = AuditLog.query.filter_by(
        action='ANONYMOUS_VOTE_ACCEPTED',
        target_type='ELECTION',
        target_id=election.id,
    ).count()
    turnout = round(votes_cast / total_verified_voters * 100, 1) if total_verified_voters else 0

    return {
        'electionId': election.id,
        'title': election.title,
        'totalVerifiedVoters': total_verified_voters,
        'votesCast': votes_cast,
        'remainingVoters': max(total_verified_voters - votes_cast, 0),
        'turnoutPercentage': min(turnout, 100.0),
        'electionStatus': status,
        'startTime': election.start_time.replace(tzinfo=INDIA_TIMEZONE).isoformat(),
        'endTime': election.end_time.replace(tzinfo=INDIA_TIMEZONE).isoformat(),
        'lastUpdated': now.replace(tzinfo=INDIA_TIMEZONE).isoformat(),
        'participation': participation,
        'auditedVotes': audited_votes,
        'auditStatus': 'OK' if audited_votes == votes_cast else 'REVIEW',
    }