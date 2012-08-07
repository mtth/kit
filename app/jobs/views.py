@app.route('/jobs')
def jobs():
    """Job history page."""
    return render_template('jobs.html')
