#!/usr/bin/env python

from app.core.util import APIError

import models as m

def lookup(**kwargs):
    query_type = kwargs['q'][0]
    if query_type == 'all_jobs':
        jobs = m.Job.query.all()
        return [job.jsonify() for job in jobs]
    if query_type == 'active_jobs':
        jobs = m.Job.query.filter(m.Job.state=='RUNNING').all()
        return [job.jsonify() for job in jobs]
    elif query_type == 'job_infos':
        if 'job_id' in kwargs:
            job = m.Job.query.get(kwargs['job_id'][0])
            if job:
                return job.jsonify()
            else:
                return 'No job found for this id.'
        else:
            raise APIError('job_infos query requires job_id parameter')
    else:
        raise APIError('Invalid query parameter: %s.' % query_type)
