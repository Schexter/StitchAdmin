    return jsonify({
        'selenium_available': selenium_available,
        'selenium_version': selenium_version,
        'chromedriver_available': chromedriver_available,
        'automation_ready': selenium_available and chromedriver_available
    })
