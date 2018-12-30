{
    "connections": [
        {
            "dst_node_id": 190,
            "dst_port_id": "i_input",
            "src_node_id": 191,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 199,
            "dst_port_id": "i_input",
            "src_node_id": 190,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 190,
            "dst_port_id": "i_time",
            "src_node_id": 193,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 197,
            "dst_port_id": "i_x",
            "src_node_id": 196,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 190,
            "dst_port_id": "i_uOffset",
            "src_node_id": 197,
            "src_port_id": "o_vec2"
        },
        {
            "dst_node_id": 203,
            "dst_port_id": "i_value",
            "src_node_id": 194,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 198,
            "dst_port_id": "i_input",
            "src_node_id": 194,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 205,
            "dst_port_id": "i_input",
            "src_node_id": 199,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 205,
            "dst_port_id": "i_enabled",
            "src_node_id": 198,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 208,
            "dst_port_id": "i_enabled",
            "src_node_id": 205,
            "src_port_id": "o_enabled"
        },
        {
            "dst_node_id": 208,
            "dst_port_id": "i_input",
            "src_node_id": 205,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 205,
            "dst_port_id": "i_timeH",
            "src_node_id": 206,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 205,
            "dst_port_id": "i_timeV",
            "src_node_id": 207,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 192,
            "dst_port_id": "i_texture",
            "src_node_id": 208,
            "src_port_id": "o_output"
        },
        {
            "dst_node_id": 208,
            "dst_port_id": "i_uRedOffset",
            "src_node_id": 209,
            "src_port_id": "o_vec2"
        }
    ],
    "nodes": [
        {
            "custom_ports": [
                [
                    "i_time",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "time",
                        "widgets": []
                    }
                ],
                [
                    "i_time_mask",
                    {
                        "default": null,
                        "dtype": "tex2d",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "time_mask",
                        "widgets": []
                    }
                ],
                [
                    "i_time_d0",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "time_d0",
                        "widgets": []
                    }
                ],
                [
                    "i_time_d1",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "time_d1",
                        "widgets": []
                    }
                ],
                [
                    "i_uThreshold",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.68
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uThreshold",
                        "widgets": []
                    }
                ],
                [
                    "i_uSoftness",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.06
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uSoftness",
                        "widgets": []
                    }
                ],
                [
                    "i_uShadeContrast",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.55
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uShadeContrast",
                        "widgets": []
                    }
                ],
                [
                    "i_uOffset",
                    {
                        "default": null,
                        "dtype": "vec2",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uOffset",
                        "widgets": []
                    }
                ]
            ],
            "id": 190,
            "manual_values": {
                "i_enable_time_mask": 0.0,
                "i_enabled": 1.0,
                "i_force_change": 42.0,
                "i_input": "",
                "i_interpolation": 1.0,
                "i_sizeref": "",
                "i_time": 0.0,
                "i_time_d0": 0.0,
                "i_time_d1": 0.0,
                "i_time_mask": "",
                "i_transformUV": [
                    [
                        1.0,
                        0.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        1.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        1.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        0.0,
                        1.0
                    ]
                ],
                "i_uOffset": [
                    0.0,
                    0.0
                ],
                "i_uShadeContrast": 0.55,
                "i_uSoftness": 0.06,
                "i_uThreshold": 0.68,
                "i_wrapping": 1.0,
                "o_enabled": 1.0,
                "o_output": ""
            },
            "type": "Rorschach",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1805.0,
                    -439.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 191,
            "manual_values": {
                "i_name": "ref_highres",
                "o_output": ""
            },
            "type": "GetTextureVar",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1278.0,
                    -416.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 192,
            "manual_values": {
                "i_texture": ""
            },
            "type": "Renderer",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2417.0,
                    -429.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 193,
            "manual_values": {
                "i_factor": 0.1599999964237213,
                "i_mod": 0.0,
                "i_reset": 0.0,
                "o_output": 164.8229632656923
            },
            "type": "Time",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1323.0,
                    -285.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 194,
            "manual_values": {
                "i_enabled": 1.0,
                "i_per_minute": 10.0,
                "o_output": 0.0
            },
            "type": "PoissonTimer",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1295.0,
                    -65.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 196,
            "manual_values": {
                "i_factor": 0.0010000000474974513,
                "i_mod": 0.0,
                "i_reset": 0.0,
                "o_output": 232.10107329539633
            },
            "type": "Time",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1243.0,
                    -559.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 197,
            "manual_values": {
                "i_x": 0.0,
                "i_y": 0.0,
                "o_vec2": [
                    232.10107421875,
                    0.0
                ]
            },
            "type": "Float2Vec2",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1510.0,
                    -486.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 198,
            "manual_values": {
                "i_condition": 1.0,
                "i_duration": 0.20000000298023224,
                "i_input": 0.0,
                "o_output": 0.0
            },
            "type": "HoldBool",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1523.0,
                    87.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [
                [
                    "i_filter_mask",
                    {
                        "default": null,
                        "dtype": "tex2d",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_mask",
                        "widgets": []
                    }
                ],
                [
                    "i_filter_mode",
                    {
                        "default": null,
                        "dtype": "int",
                        "dtype_args": {
                            "choices": [
                                "input",
                                "mask",
                                "filtered",
                                "input_filtered_masked",
                                "input_masked",
                                "filtered_masked"
                            ],
                            "default": 2.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_mode",
                        "widgets": []
                    }
                ],
                [
                    "i_filter_bg",
                    {
                        "default": null,
                        "dtype": "color",
                        "dtype_args": {
                            "default": [
                                0.0,
                                0.0,
                                0.0,
                                0.0
                            ]
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_bg",
                        "widgets": []
                    }
                ],
                [
                    "i_time",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "time",
                        "widgets": []
                    }
                ],
                [
                    "i_amount",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "amount",
                        "widgets": []
                    }
                ],
                [
                    "i_speed",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "speed",
                        "widgets": []
                    }
                ]
            ],
            "id": 199,
            "manual_values": {
                "i_advanced_filtering": 0.0,
                "i_amount": 0.27000001072883606,
                "i_enabled": 0.0,
                "i_filter_bg": [
                    0.0,
                    0.0,
                    0.0,
                    0.0
                ],
                "i_filter_mask": "",
                "i_filter_mode": 2.0,
                "i_force_change": 42.0,
                "i_input": "",
                "i_interpolation": 1.0,
                "i_sizeref": "",
                "i_speed": 0.10000000149011612,
                "i_time": 0.0,
                "i_transformUV": [
                    [
                        1.0,
                        0.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        1.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        1.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        0.0,
                        1.0
                    ]
                ],
                "i_wrapping": 1.0,
                "o_enabled": 0.0,
                "o_output": ""
            },
            "type": "Glitch",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2183.0,
                    -267.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 201,
            "manual_values": {
                "i_factor": 1.0,
                "i_mod": 0.0,
                "i_reset": 0.0,
                "o_output": 432.7406404018402
            },
            "type": "Time",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1740.0,
                    -54.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 203,
            "manual_values": {
                "i_threshold": 0.8999999761581421,
                "i_value": 0.0,
                "o_combined": 0.0,
                "o_falling": 0.0,
                "o_rising": 0.0
            },
            "type": "Edge",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    1790.0,
                    111.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [
                [
                    "i_filter_mask",
                    {
                        "default": null,
                        "dtype": "tex2d",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_mask",
                        "widgets": []
                    }
                ],
                [
                    "i_filter_mode",
                    {
                        "default": null,
                        "dtype": "int",
                        "dtype_args": {
                            "choices": [
                                "input",
                                "mask",
                                "filtered",
                                "input_filtered_masked",
                                "input_masked",
                                "filtered_masked"
                            ],
                            "default": 2.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_mode",
                        "widgets": []
                    }
                ],
                [
                    "i_filter_bg",
                    {
                        "default": null,
                        "dtype": "color",
                        "dtype_args": {
                            "default": [
                                0.0,
                                0.0,
                                0.0,
                                0.0
                            ]
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_bg",
                        "widgets": []
                    }
                ],
                [
                    "i_slices",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 3.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "slices",
                        "widgets": []
                    }
                ],
                [
                    "i_offset",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 100.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "offset",
                        "widgets": []
                    }
                ],
                [
                    "i_timeH",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "timeH",
                        "widgets": []
                    }
                ],
                [
                    "i_timeV",
                    {
                        "default": null,
                        "dtype": "float",
                        "dtype_args": {
                            "default": 0.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "timeV",
                        "widgets": []
                    }
                ]
            ],
            "id": 205,
            "manual_values": {
                "i_advanced_filtering": 0.0,
                "i_enabled": 1.0,
                "i_filter_bg": [
                    0.0,
                    0.0,
                    0.0,
                    0.0
                ],
                "i_filter_mask": "",
                "i_filter_mode": 2.0,
                "i_force_change": 42.0,
                "i_input": "",
                "i_interpolation": 1.0,
                "i_offset": 100.0,
                "i_sizeref": "",
                "i_slices": 5.0,
                "i_timeH": 3.200000047683716,
                "i_timeV": 1.8799999952316284,
                "i_transformUV": [
                    [
                        1.0,
                        0.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        1.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        1.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        0.0,
                        1.0
                    ]
                ],
                "i_wrapping": 1.0,
                "o_enabled": 0.0,
                "o_output": ""
            },
            "type": "Slices",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2395.0,
                    -51.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 206,
            "manual_values": {
                "i_factor": 0.10000000149011612,
                "i_mod": 0.0,
                "i_reset": 0.0,
                "o_output": 24.186515426735433
            },
            "type": "Time",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2075.0,
                    60.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 207,
            "manual_values": {
                "i_factor": 0.10000000149011612,
                "i_mod": 0.0,
                "i_reset": 0.0,
                "o_output": 22.229883477537072
            },
            "type": "Time",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2115.0,
                    190.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [
                [
                    "i_filter_mask",
                    {
                        "default": null,
                        "dtype": "tex2d",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_mask",
                        "widgets": []
                    }
                ],
                [
                    "i_filter_mode",
                    {
                        "default": null,
                        "dtype": "int",
                        "dtype_args": {
                            "choices": [
                                "input",
                                "mask",
                                "filtered",
                                "input_filtered_masked",
                                "input_masked",
                                "filtered_masked"
                            ],
                            "default": 2.0
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_mode",
                        "widgets": []
                    }
                ],
                [
                    "i_filter_bg",
                    {
                        "default": null,
                        "dtype": "color",
                        "dtype_args": {
                            "default": [
                                0.0,
                                0.0,
                                0.0,
                                0.0
                            ]
                        },
                        "dummy": false,
                        "group": "default",
                        "hide": true,
                        "manual_input": true,
                        "name": "filter_bg",
                        "widgets": []
                    }
                ],
                [
                    "i_uRedOffset",
                    {
                        "default": null,
                        "dtype": "vec2",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uRedOffset",
                        "widgets": []
                    }
                ],
                [
                    "i_uGreenOffset",
                    {
                        "default": null,
                        "dtype": "vec2",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uGreenOffset",
                        "widgets": []
                    }
                ],
                [
                    "i_uBlueOffset",
                    {
                        "default": null,
                        "dtype": "vec2",
                        "dtype_args": {},
                        "dummy": false,
                        "group": "default",
                        "hide": false,
                        "manual_input": true,
                        "name": "uBlueOffset",
                        "widgets": []
                    }
                ]
            ],
            "id": 208,
            "manual_values": {
                "i_advanced_filtering": 0.0,
                "i_enabled": 1.0,
                "i_filter_bg": [
                    0.0,
                    0.0,
                    0.0,
                    0.0
                ],
                "i_filter_mask": "",
                "i_filter_mode": 2.0,
                "i_force_change": 42.0,
                "i_input": "",
                "i_interpolation": 1.0,
                "i_sizeref": "",
                "i_transformUV": [
                    [
                        1.0,
                        0.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        1.0,
                        0.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        1.0,
                        0.0
                    ],
                    [
                        0.0,
                        0.0,
                        0.0,
                        1.0
                    ]
                ],
                "i_uBlueOffset": [
                    0.0,
                    0.0
                ],
                "i_uGreenOffset": [
                    0.0,
                    0.0
                ],
                "i_uRedOffset": [
                    0.0,
                    0.0
                ],
                "i_wrapping": 1.0,
                "o_enabled": 0.0,
                "o_output": ""
            },
            "type": "ChromaticAberration",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2700.0,
                    -78.0
                ],
                "selected": false
            }
        },
        {
            "custom_ports": [],
            "id": 209,
            "manual_values": {
                "i_x": -9.260000228881836,
                "i_y": 0.0,
                "o_vec2": [
                    -9.260000228881836,
                    0.0
                ]
            },
            "type": "Float2Vec2",
            "ui_data": {
                "collapsed": false,
                "pos": [
                    2638.0,
                    182.0
                ],
                "selected": false
            }
        }
    ],
    "ui_data": {
        "offset": [
            1069.0,
            -695.0
        ]
    }
}